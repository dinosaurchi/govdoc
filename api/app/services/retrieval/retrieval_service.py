import math


class RetrievalService:
    def __init__(self, embed_fn=None, rerank_fn=None, reference_chunks: list[dict] | None = None):
        self.embed_fn = embed_fn  # function(texts: list[str]) -> list[EmbeddingResult]
        self.rerank_fn = rerank_fn  # function(query, documents, top_n) -> list[RerankResult]
        self.reference_chunks = reference_chunks or []
        self._embeddings_cache: dict[int, list[float]] = {}

    def set_references(self, chunks: list[dict]):
        """Set reference chunks. Each chunk: {"id": str, "text": str, "source": str}."""
        self.reference_chunks = chunks
        self._embeddings_cache.clear()

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search reference corpus for relevant chunks."""
        if not self.reference_chunks:
            return []

        # If embed function available, use cosine similarity
        if self.embed_fn:
            return self._semantic_search(query, top_k)

        # Fallback: simple text matching
        return self._keyword_search(query, top_k)

    def _semantic_search(self, query: str, top_k: int) -> list[dict]:
        texts = [c["text"] for c in self.reference_chunks]
        all_texts = [query] + texts

        try:
            results = self.embed_fn(all_texts)
            query_embedding = results[0].embedding

            scored = []
            for i, chunk in enumerate(self.reference_chunks):
                chunk_embedding = results[i + 1].embedding
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                scored.append({"chunk": chunk, "score": similarity})

            scored.sort(key=lambda x: x["score"], reverse=True)
            top_results = scored[:top_k]

            # Optionally rerank
            if self.rerank_fn and len(top_results) > 1:
                doc_texts = [r["chunk"]["text"] for r in top_results]
                reranked = self.rerank_fn(query, doc_texts, top_n=top_k)
                final = []
                for rr in reranked:
                    chunk = top_results[rr.index]["chunk"]
                    final.append(
                        {
                            "id": chunk.get("id"),
                            "text": rr.text,
                            "source": chunk.get("source"),
                            "score": rr.relevance_score,
                        }
                    )
                return final

            return [
                {
                    "id": r["chunk"].get("id"),
                    "text": r["chunk"]["text"],
                    "source": r["chunk"].get("source"),
                    "score": r["score"],
                }
                for r in top_results
            ]
        except Exception:
            return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[dict]:
        query_lower = query.lower()
        scored = []
        for chunk in self.reference_chunks:
            overlap = len(set(query_lower.split()) & set(chunk["text"].lower().split()))
            scored.append({"chunk": chunk, "score": overlap})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return [
            {
                "id": r["chunk"].get("id"),
                "text": r["chunk"]["text"],
                "source": r["chunk"].get("source"),
                "score": r["score"],
            }
            for r in scored[:top_k]
        ]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
