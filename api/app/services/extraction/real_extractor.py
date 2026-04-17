from pypdf import PdfReader
from app.models.document import ExtractionMethod
from pathlib import Path


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
