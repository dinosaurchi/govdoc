from app.services.extraction.interface import ExtractionProviderInterface
from typing import Dict, Any

class MockExtractionProvider(ExtractionProviderInterface):
    async def extract_text(self, file_path: str) -> str:
        return "Sample extracted text from " + file_path

    async def extract_structured_data(self, file_path: str) -> Dict[str, Any]:
        return {
            "document_number": "123/CV-VP",
            "date": "2026-04-16",
            "sender": "Bộ Công Thương"
        }
