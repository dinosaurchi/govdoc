import io
from pathlib import Path

import pytest
from pypdf import PdfWriter

from app.models.document import ExtractionMethod
from app.services.extraction.real_extractor import RealExtractor


@pytest.fixture
def extractor():
    return RealExtractor()


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


def _make_blank_pdf(tmp_dir: Path) -> str:
    """Create a blank PDF (no embedded text) for scan detection tests."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    path = tmp_dir / "blank.pdf"
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    path.write_bytes(buf.read())
    return str(path)


def _make_text_file(tmp_dir: Path, content: str = "This is a test document for GovDoc extraction.") -> str:
    path = tmp_dir / "test.txt"
    path.write_text(content, encoding="utf-8")
    return str(path)


@pytest.mark.unit
class TestPlainTextExtraction:
    def test_extract_plaintext(self, extractor, tmp_dir):
        content = "This is a plain text document for testing the GovDoc extraction pipeline."
        path = _make_text_file(tmp_dir, content)
        result = extractor.extract_text(path, "test.txt", "text/plain")
        assert result.text == content
        assert result.method == ExtractionMethod.plaintext
        assert result.page_count == 1
        assert result.warnings == []

    def test_extract_plaintext_utf8(self, extractor, tmp_dir):
        content = "V/v đề xuất tăng cường công tác quản lý hồ sơ hành chính"
        path = _make_text_file(tmp_dir, content)
        result = extractor.extract_text(path, "test.txt", "text/plain")
        assert result.text == content


@pytest.mark.unit
class TestPDFExtraction:
    def test_blank_pdf_returns_empty_text(self, extractor, tmp_dir):
        """Blank PDF has no embedded text — should trigger scan detection."""
        path = _make_blank_pdf(tmp_dir)
        result = extractor.extract_text(path, "blank.pdf", "application/pdf")
        assert result.text == ""
        assert result.method == ExtractionMethod.render_ocr
        assert result.page_count == 1
        assert "OCR required" in result.warnings[0]

    def test_has_text_false_for_blank_pdf(self, extractor, tmp_dir):
        path = _make_blank_pdf(tmp_dir)
        result = extractor.extract_text(path, "blank.pdf", "application/pdf")
        assert extractor.has_text(result) is False

    def test_has_text_true_for_plaintext(self, extractor, tmp_dir):
        path = _make_text_file(tmp_dir, "This is a meaningful document with enough text content to pass the threshold.")
        result = extractor.extract_text(path, "test.txt", "text/plain")
        assert extractor.has_text(result) is True


@pytest.mark.unit
class TestUnsupportedMimeType:
    def test_unsupported_mime_raises(self, extractor, tmp_dir):
        path = _make_text_file(tmp_dir, "content")
        with pytest.raises(ValueError, match="Unsupported mime type"):
            extractor.extract_text(path, "test.xyz", "application/x-unknown")

    def test_image_mime_returns_empty_with_warning(self, extractor, tmp_dir):
        path = _make_text_file(tmp_dir, "fake image")
        result = extractor.extract_text(path, "photo.png", "image/png")
        assert result.text == ""
        assert result.method == ExtractionMethod.qwen_ocr
        assert "OCR required" in result.warnings[0]


@pytest.mark.unit
class TestExtractionResult:
    def test_default_warnings_empty(self):
        from app.services.extraction.real_extractor import ExtractionResult

        result = ExtractionResult(text="hello", method=ExtractionMethod.plaintext)
        assert result.warnings == []

    def test_custom_warnings(self):
        from app.services.extraction.real_extractor import ExtractionResult

        result = ExtractionResult(text="", method=ExtractionMethod.render_ocr, warnings=["scan detected"])
        assert result.warnings == ["scan detected"]
