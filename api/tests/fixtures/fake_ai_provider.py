"""Test-only fake AI provider.

Used exclusively in tests via FastAPI `app.dependency_overrides` so that
integration tests don't require live Model Studio credentials or hit the
network. Production code must never import this module.
"""

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


class FakeAIProvider(AIProvider):
    """Deterministic stand-in for RealAIProvider in tests."""

    @staticmethod
    def _find_department_id(
        departments: list[dict] | None,
        *preferred_ids: str,
    ) -> str:
        if departments:
            for preferred in preferred_ids:
                for department in departments:
                    if department["id"] == preferred:
                        return department["id"]
            return departments[0]["id"]
        return preferred_ids[0] if preferred_ids else "phong_hanh_chinh"

    def classify(self, text: str, departments: list[dict] | None = None) -> ClassificationResult:
        return ClassificationResult(
            doc_type="cong_van",
            confidence=0.85,
            rationale="Test classification rationale",
            issuing_agency="Test Agency",
            urgency="normal",
            confidentiality="unclassified",
        )

    def summarize(self, text: str) -> SummaryResult:
        return SummaryResult(
            summary_points=["Test summary point 1", "Test summary point 2"],
            key_subject="Test subject",
            key_entities=["Entity A", "Entity B"],
        )

    def route(self, text: str, departments: list[dict]) -> RoutingResult:
        lowered = text.lower()
        finance = self._find_department_id(departments, "phong_tai_chinh", "phong_hanh_chinh")
        legal = self._find_department_id(departments, "phong_phap_che", "phong_ke_hoach")
        planning = self._find_department_id(departments, "phong_ke_hoach", "phong_hanh_chinh")
        admin = self._find_department_id(departments, "phong_hanh_chinh")
        is_ambiguity_doc = any(
            marker in lowered
            for marker in (
                "bộ tư pháp",
                "ý kiến",
                "y kien",
                "nghị định số 113/2014",
                "nghi dinh so 113/2014",
                "hợp tác quốc tế về pháp luật",
                "hop tac quoc te ve phap luat",
            )
        )

        if "mua s" in lowered or "kinh ph" in lowered or "xe " in lowered:
            return RoutingResult(
                suggested_department=finance,
                secondary_department=admin,
                routing_confidence=0.91,
                routing_rationale="Procurement and budget language suggests Finance should lead.",
                needs_consultation=False,
                needs_supervisor_review=False,
            )

        if is_ambiguity_doc:
            return RoutingResult(
                suggested_department=legal,
                secondary_department=planning,
                routing_confidence=0.58,
                routing_rationale="The document spans legal interpretation and planning impact, so the route is ambiguous.",
                needs_consultation=True,
                needs_supervisor_review=True,
            )

        if "test ocr output" in lowered:
            return RoutingResult(
                suggested_department=admin,
                secondary_department=finance,
                routing_confidence=0.76,
                routing_rationale="Recovered OCR text is enough for administrative triage.",
                needs_consultation=False,
                needs_supervisor_review=False,
            )

        dept_id = departments[0]["id"] if departments else "phong_hanh_chinh"
        return RoutingResult(
            suggested_department=dept_id,
            secondary_department=None,
            routing_confidence=0.9,
            routing_rationale="Test routing rationale",
            needs_consultation=False,
            needs_supervisor_review=False,
        )

    def escalate(self, text: str, departments: list[dict]) -> EscalationResult:
        lowered = text.lower()
        dept_id = departments[0]["id"] if departments else "phong_hanh_chinh"
        alt_ids = [d["id"] for d in departments[1:]] if len(departments) > 1 else []
        if any(
            marker in lowered
            for marker in (
                "bộ tư pháp",
                "ý kiến",
                "y kien",
                "nghị định số 113/2014",
                "nghi dinh so 113/2014",
                "hợp tác quốc tế về pháp luật",
                "hop tac quoc te ve phap luat",
            )
        ):
            dept_id = self._find_department_id(departments, "phong_phap_che", "phong_ke_hoach")
            planning = self._find_department_id(departments, "phong_ke_hoach", dept_id)
            alt_ids = [planning] + [item for item in alt_ids if item != planning]
        conf_per_dept = (
            {d["id"]: round(0.6 - i * 0.1, 2) for i, d in enumerate(departments)} if departments else {}
        )
        return EscalationResult(
            primary_recommendation=dept_id,
            alternatives=alt_ids,
            ambiguity_explanation="Cross-department overlap requires explicit escalation review.",
            confidence_per_department=conf_per_dept,
            final_confidence=0.5,
            needs_consultation=True,
            consultation_reason="The document impacts more than one department.",
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
            text="Test OCR output",
            page_count=1,
            extraction_method="qwen-ocr",
            warnings=[],
        )
