from abc import ABC, abstractmethod
from typing import Dict, Any, List

class RetrievalProviderInterface(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents or sections."""
        pass
