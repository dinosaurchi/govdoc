"""DashScope rerank client per §17."""

from __future__ import annotations

import httpx

from app.adapters.modelstudio.schemas import RerankResult
from app.core.config import settings


class RerankClient:
    def __init__(self) -> None:
        settings.validate_ai_config()
        self.client = httpx.Client(timeout=120.0)
        self.base_url = settings.MODELSTUDIO_DASHSCOPE_URL

    def rerank(
        self,
        query: str,
        documents: list[str],
        model: str = "qwen3-rerank",
        top_n: int = 5,
    ) -> list[RerankResult]:
        """Rerank documents against query using DashScope rerank endpoint."""
        payload = {
            "model": model,
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": {
                "top_n": top_n,
                "return_documents": True,
            },
        }

        resp = self.client.post(
            f"{self.base_url}/services/rerank/text-rerank/text-rerank",
            headers={
                "Authorization": f"Bearer {settings.MODELSTUDIO_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if resp.status_code != 200:
            raise RuntimeError(f"Rerank API error: {resp.status_code} {resp.text}")

        results = resp.json()["output"]["results"]
        return [
            RerankResult(
                index=r["index"],
                relevance_score=r["relevance_score"],
                text=r["document"]["text"],
            )
            for r in results
        ]
