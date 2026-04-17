from abc import ABC, abstractmethod
from typing import Dict, Any, List

class ExtractionProviderInterface(ABC):
    @abstractmethod
    async def extract_text(self, file_path: str) -> str:
        """Extract raw text from a file."""
        pass

    @abstractmethod
    async def extract_structured_data(self, file_path: str) -> Dict[str, Any]:
        """Extract keys/values from the document."""
        pass
