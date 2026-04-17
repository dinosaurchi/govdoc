from __future__ import annotations

from pydantic import BaseModel
from datetime import datetime
from typing import Any


# Enums for schemas
class DocumentStatusSchema(str):
    received = "received"
    extracted = "extracted"
    analyzed = "analyzed"
    routed = "routed"
    under_review = "under_review"
    in_consultation = "in_consultation"
    approved = "approved"
    closed = "closed"
    out_of_scope = "out_of_scope"
    ingest_failed = "ingest_failed"
    analysis_failed = "analysis_failed"


class SecurityLevelSchema(str):
    unclassified = "unclassified"
    confidential = "confidential"
    secret = "secret"
    top_secret = "top_secret"


class UrgencySchema(str):
    normal = "normal"
    urgent = "urgent"
    critical = "critical"


class ExtractionMethodSchema(str):
    pypdf = "pypdf"
    render_ocr = "render_ocr"
    qwen_ocr = "qwen-ocr"
    docx = "docx"
    plaintext = "plaintext"


class AnalysisStageSchema(str):
    classify = "classify"
    summarize = "summarize"
    route = "route"
    escalate = "escalate"


class AnalysisSourceSchema(str):
    live = "live"
    cached = "cached"


class RoutingDecisionTypeSchema(str):
    accepted = "accepted"
    rerouted = "rerouted"
    escalated = "escalated"
    out_of_scope = "out_of_scope"


# Document schemas
class DocumentCreate(BaseModel):
    title: str


class DocumentOut(BaseModel):
    id: str
    title: str
    doc_number: str | None = None
    issuing_agency: str | None = None
    received_at: datetime
    status: str
    security_level: str
    urgency: str
    assigned_department_id: str | None = None
    assigned_reviewer_role: str | None = None
    current_prompt_version: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListOut(BaseModel):
    id: str
    title: str
    doc_number: str | None = None
    status: str
    security_level: str
    urgency: str
    assigned_department_id: str | None = None
    created_at: datetime
    consultation_notes: list[ConsultationNoteOut] = []

    class Config:
        from_attributes = True


class DocumentFilters(BaseModel):
    status: str | None = None
    department_id: str | None = None
    q: str | None = None
    scenario: str | None = None


class DocumentFileOut(BaseModel):
    id: str
    document_id: str
    storage_key: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ExtractedArtifactOut(BaseModel):
    id: str
    document_id: str
    extraction_method: str
    text: str
    page_count: int
    warnings: list[str] = []
    extracted_at: datetime

    class Config:
        from_attributes = True


class AIAnalysisOut(BaseModel):
    id: str
    document_id: str
    stage: str
    model_name: str
    prompt_version: str
    source: str
    payload_json: dict[str, Any]
    confidence: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class RoutingDecisionOut(BaseModel):
    id: str
    document_id: str
    suggested_department_id: str | None = None
    final_department_id: str | None = None
    decided_by_role: str | None = None
    decision: str
    rationale: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConsultationNoteOut(BaseModel):
    id: str
    document_id: str
    author_role: str
    target_role: str | None = None
    body: str
    resolved_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditEventOut(BaseModel):
    id: str
    document_id: str | None = None
    actor_role: str | None = None
    event_type: str
    from_state: str | None = None
    to_state: str | None = None
    metadata_json: dict[str, Any] = {}
    occurred_at: datetime

    class Config:
        from_attributes = True


class DocumentDetailOut(DocumentOut):
    files: list[DocumentFileOut] = []
    artifacts: list[ExtractedArtifactOut] = []
    analyses: list[AIAnalysisOut] = []
    routing_decisions: list[RoutingDecisionOut] = []
    consultation_notes: list[ConsultationNoteOut] = []
    audit_events: list[AuditEventOut] = []


class UploadResponse(BaseModel):
    document: DocumentOut
    extracted_artifact: ExtractedArtifactOut | None = None
    ai_analyses: list[AIAnalysisOut] = []


class RerouteRequest(BaseModel):
    department_id: str
    rationale: str | None = None


class ConsultationRequest(BaseModel):
    target_role: str
    body: str


class WorkflowActionResponse(BaseModel):
    """Generic response for workflow action endpoints."""

    document: DocumentOut
    message: str | None = None


class RoutingActionResponse(BaseModel):
    document: DocumentOut
    routing_decision: RoutingDecisionOut


class ConsultationActionResponse(BaseModel):
    document: DocumentOut
    consultation_note: ConsultationNoteOut
