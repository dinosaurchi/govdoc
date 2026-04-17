from app.services.retrieval.interface import RetrievalProviderInterface
from typing import Dict, Any, List

class MockRetrievalProvider(RetrievalProviderInterface):
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        return [
            {"id": "REF-001", "score": 0.95, "text": "Related policy regarding IT maintenance."},
            {"id": "REF-002", "score": 0.82, "text": "Previous decision on budget allocation."}
        ]
