from app.services.extraction.interface import ExtractionProviderInterface
from typing import Dict, Any


class MockExtractionProvider(ExtractionProviderInterface):
    """Mock only — replace with real PDF/DOCX extraction in a later pass."""

    source_label = "MockExtractionProvider (deterministic placeholder)"

    async def extract_text(self, file_path: str) -> str:
        return (
            "[Mock extraction] Normalized text preview for uploaded file. "
            f"Source path: {file_path}. "
            "Real OCR or parser output will replace this in Pass 3+."
        )

    async def extract_structured_data(self, file_path: str) -> Dict[str, Any]:
        return {
            "document_number": "123/CV-VP",
            "date": "2026-04-16",
            "sender": "Bộ Công Thương",
            "mock": True,
        }
