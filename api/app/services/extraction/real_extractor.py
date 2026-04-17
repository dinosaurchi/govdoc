import base64
import io
from pathlib import Path
from typing import Callable

from pypdf import PdfReader

from app.adapters.modelstudio.schemas import OCRResult
from app.models.document import ExtractionMethod


class ExtractionResult:
    def __init__(self, text: str, method: ExtractionMethod, page_count: int = 1, warnings: list[str] | None = None):
        self.text = text
        self.method = method
        self.page_count = page_count
        self.warnings = warnings or []


class RealExtractor:
    def extract_text(self, file_path: str, filename: str, mime_type: str) -> ExtractionResult:
        """Extract text from file based on mime type."""
        if mime_type == "application/pdf":
            return self._extract_pdf(file_path)
        elif mime_type in ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",):
            return self._extract_docx(file_path)
        elif mime_type.startswith("text/"):
            return self._extract_plaintext(file_path)
        elif mime_type.startswith("image/"):
            return ExtractionResult(text="", method=ExtractionMethod.qwen_ocr, warnings=["Image file — OCR required"])
        else:
            raise ValueError(f"Unsupported mime type: {mime_type}")

    def _extract_pdf(self, file_path: str) -> ExtractionResult:
        """Extract text from PDF using pypdf."""
        reader = PdfReader(file_path)
        text_parts = []
        page_count = len(reader.pages)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
        full_text = "\n\n".join(text_parts).strip()

        if not full_text:
            return ExtractionResult(
                text="",
                method=ExtractionMethod.render_ocr,
                page_count=page_count,
                warnings=["PDF has no embedded text — OCR required"],
            )

        return ExtractionResult(
            text=full_text,
            method=ExtractionMethod.pypdf,
            page_count=page_count,
        )

    def _extract_docx(self, file_path: str) -> ExtractionResult:
        """Extract text from DOCX using python-docx."""
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument(file_path)
            text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
            return ExtractionResult(text=text, method=ExtractionMethod.docx)
        except ImportError:
            raise ValueError("python-docx not installed")

    def _extract_plaintext(self, file_path: str) -> ExtractionResult:
        """Read plain text file."""
        text = Path(file_path).read_text(encoding="utf-8")
        return ExtractionResult(text=text, method=ExtractionMethod.plaintext)

    def has_text(self, result: ExtractionResult) -> bool:
        """Check if extraction produced meaningful text."""
        return bool(result.text and len(result.text.strip()) > 10)

    # ── OCR fallback ───────────────────────────────────────────────────
    def extract_with_ocr(
        self,
        file_path: str,
        mime_type: str,
        ocr_fn: Callable[[str], OCRResult],
        max_pages: int = 3,
    ) -> ExtractionResult:
        """Render the file to images and run ``ocr_fn`` on each page.

        For PDFs this renders up to ``max_pages`` pages via ``pdf2image`` at
        150 DPI, encodes each page as base64 PNG, and concatenates the OCR
        text. For image inputs the file bytes are base64-encoded directly.

        Per the fail-fast rule, raises ``ValueError`` if the OCR pass yields
        no text — callers must NOT silently degrade.
        """
        if mime_type == "application/pdf":
            return self._ocr_pdf(file_path, ocr_fn, max_pages)
        if mime_type in ("image/png", "image/jpeg", "image/jpg"):
            return self._ocr_image(file_path, ocr_fn)
        raise ValueError(f"OCR not supported for mime type: {mime_type}")

    def _ocr_pdf(
        self,
        file_path: str,
        ocr_fn: Callable[[str], OCRResult],
        max_pages: int,
    ) -> ExtractionResult:
        from pdf2image import convert_from_path

        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        last_page = min(max_pages, total_pages) if total_pages else max_pages

        images = convert_from_path(
            file_path,
            dpi=150,
            first_page=1,
            last_page=last_page,
        )

        page_texts: list[str] = []
        for image in images:
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            ocr_result = ocr_fn(b64)
            page_texts.append(ocr_result.text or "")

        full_text = "\n\n".join(t for t in page_texts).strip()
        rendered = len(images)

        if not full_text:
            raise ValueError("OCR produced empty text")

        return ExtractionResult(
            text=full_text,
            method=ExtractionMethod.render_ocr,
            page_count=rendered,
            warnings=[f"Rendered {rendered} page(s) via pdf2image + Qwen-VL"],
        )

    def _ocr_image(
        self,
        file_path: str,
        ocr_fn: Callable[[str], OCRResult],
    ) -> ExtractionResult:
        data = Path(file_path).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        ocr_result = ocr_fn(b64)
        text = (ocr_result.text or "").strip()
        if not text:
            raise ValueError("OCR produced empty text")
        return ExtractionResult(
            text=text,
            method=ExtractionMethod.qwen_ocr,
            page_count=1,
            warnings=["Rendered 1 page(s) via pdf2image + Qwen-VL"],
        )
