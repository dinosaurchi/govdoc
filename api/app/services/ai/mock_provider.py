"""Mock AI provider for development/testing, updated for new interface."""

from __future__ import annotations

from app.adapters.modelstudio.schemas import (
    ClassificationResult,
    EmbeddingResult,
    EscalationResult,
    OCRResult,
    RoutingResult,
    SummaryResult,
)
from app.services.ai.interface import AIProvider


class MockAIProvider(AIProvider):
    source_label = "MockAIProvider (replace with Model Studio adapter)"

    def classify(self, text: str, departments: list[dict] | None = None) -> ClassificationResult:
        return ClassificationResult(
            doc_type="cong_van",
            confidence=0.85,
            rationale="Mock classification rationale",
            issuing_agency="Mock Agency",
            urgency="normal",
            confidentiality="unclassified",
        )

    def summarize(self, text: str) -> SummaryResult:
        return SummaryResult(
            summary_points=["Mock summary point 1", "Mock summary point 2"],
            key_subject="Mock subject",
            key_entities=["Entity A", "Entity B"],
        )

    def route(self, text: str, departments: list[dict]) -> RoutingResult:
        dept_id = departments[0]["id"] if departments else "phong_hanh_chinh"
        return RoutingResult(
            suggested_department=dept_id,
            secondary_department=None,
            routing_confidence=0.9,
            routing_rationale="Mock routing rationale",
            needs_consultation=False,
            needs_supervisor_review=False,
        )

    def escalate(self, text: str, departments: list[dict]) -> EscalationResult:
        dept_id = departments[0]["id"] if departments else "phong_hanh_chinh"
        alt_ids = [d["id"] for d in departments[1:]] if len(departments) > 1 else []
        conf_per_dept = {d["id"]: round(0.6 - i * 0.1, 2) for i, d in enumerate(departments)} if departments else {}
        return EscalationResult(
            primary_recommendation=dept_id,
            alternatives=alt_ids,
            ambiguity_explanation="Mock ambiguity",
            confidence_per_department=conf_per_dept,
            final_confidence=0.5,
            needs_consultation=True,
            consultation_reason="Mock consultation reason",
        )

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(
                embedding=[0.1] * 1024,
                model="text-embedding-v4",
                total_tokens=len(t.split()),
            )
            for t in texts
        ]

    def ocr(self, image_base64: str) -> OCRResult:
        return OCRResult(
            text="Mock OCR output",
            page_count=1,
            extraction_method="qwen-ocr",
            warnings=[],
        )

    # Backward-compat for existing endpoint
    async def analyze_document(self, content: str) -> dict:
        return {
            "suggested_type": "công văn",
            "urgency_score": 3,
            "summary": "This is a mock analysis of the document.",
            "suggested_department": "Hành chính",
            "entities": ["Company A", "Request X"],
        }

    async def summarize_text(self, text: str) -> str:
        return "Mock summary for: " + text[:50] + "..."
