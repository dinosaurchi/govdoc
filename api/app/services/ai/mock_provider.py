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
        return RoutingResult(
            suggested_department="phong_hanh_chinh",
            secondary_department=None,
            routing_confidence=0.75,
            routing_rationale="Mock routing rationale",
            needs_consultation=False,
            needs_supervisor_review=False,
        )

    def escalate(self, text: str, departments: list[dict]) -> EscalationResult:
        return EscalationResult(
            primary_recommendation="phong_hanh_chinh",
            alternatives=["phong_phap_che"],
            ambiguity_explanation="Mock ambiguity",
            confidence_per_department={"phong_hanh_chinh": 0.6, "phong_phap_che": 0.4},
            final_confidence=0.6,
            needs_consultation=False,
            consultation_reason=None,
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
