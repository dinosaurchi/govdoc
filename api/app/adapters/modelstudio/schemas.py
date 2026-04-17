"""Pydantic AI output schemas per §17.4."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    doc_type: str  # one of: cong_van, quyet_dinh, thong_bao, to_trinh, bao_cao, other
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    issuing_agency: str | None = None
    urgency: str = "normal"  # normal | urgent | critical
    confidentiality: str = "unclassified"  # unclassified | confidential | secret | top_secret


class SummaryResult(BaseModel):
    summary_points: list[str]
    key_subject: str
    key_entities: list[str]


class RoutingResult(BaseModel):
    suggested_department: str
    secondary_department: str | None = None
    routing_confidence: float = Field(ge=0.0, le=1.0)
    routing_rationale: str
    needs_consultation: bool = False
    needs_supervisor_review: bool = False


class EscalationResult(BaseModel):
    primary_recommendation: str
    alternatives: list[str]
    ambiguity_explanation: str
    confidence_per_department: dict[str, float]
    final_confidence: float = Field(ge=0.0, le=1.0)
    needs_consultation: bool
    consultation_reason: str | None = None


class EmbeddingResult(BaseModel):
    embedding: list[float]
    model: str
    total_tokens: int


class RerankResult(BaseModel):
    index: int
    relevance_score: float
    text: str


class OCRResult(BaseModel):
    text: str
    page_count: int = 1
    extraction_method: str = "qwen-ocr"
    warnings: list[str] = []
