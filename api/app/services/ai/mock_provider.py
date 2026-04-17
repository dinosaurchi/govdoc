from app.services.ai.interface import AIProviderInterface
from typing import Dict, Any

class MockAIProvider(AIProviderInterface):
    source_label = "MockAIProvider (replace with Model Studio adapter)"

    async def analyze_document(self, content: str) -> Dict[str, Any]:
        return {
            "suggested_type": "công văn",
            "urgency_score": 3,
            "summary": "This is a mock analysis of the document.",
            "suggested_department": "Hành chính",
            "entities": ["Company A", "Request X"]
        }

    async def summarize(self, text: str) -> str:
        return "Mock summary for: " + text[:50] + "..."
