from abc import ABC, abstractmethod
from typing import Dict, Any

class AIProviderInterface(ABC):
    @abstractmethod
    async def analyze_document(self, content: str) -> Dict[str, Any]:
        """Analyze document text and return structured analysis."""
        pass

    @abstractmethod
    async def summarize(self, text: str) -> str:
        """Return a concise summary of the text."""
        pass
