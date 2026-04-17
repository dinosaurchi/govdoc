from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Any

from app.models.document import DocumentStatus, SecurityLevel, Urgency


class DocumentBase(BaseModel):
    title: str


class DocumentCreate(DocumentBase):
    doc_number: Optional[str] = None
    issuing_agency: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.unclassified
    urgency: Urgency = Urgency.normal


class DocumentFileOut(BaseModel):
    id: str
    storage_key: str
    original_filename: str
    mime_type: str
    size_bytes: int
    sha256: str
    is_primary: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractedArtifactOut(BaseModel):
    id: str
    extraction_method: str
    text: str
    page_count: int = 1
    warnings: Optional[list[str]] = None
    extracted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIAnalysisOut(BaseModel):
    id: str
    stage: str
    model_name: str
    prompt_version: str
    source: str
    payload_json: Any
    confidence: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoutingDecisionOut(BaseModel):
    id: str
    suggested_department_id: Optional[str] = None
    final_department_id: Optional[str] = None
    decided_by_role: Optional[str] = None
    decision: str
    rationale: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsultationNoteOut(BaseModel):
    id: str
    author_role: str
    target_role: Optional[str] = None
    body: str
    resolved_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditEventOut(BaseModel):
    id: str
    document_id: Optional[str] = None
    actor_role: Optional[str] = None
    event_type: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    metadata_json: Optional[dict[str, Any]] = None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentOut(DocumentBase):
    id: str
    doc_number: Optional[str] = None
    issuing_agency: Optional[str] = None
    received_at: datetime
    status: DocumentStatus
    security_level: SecurityLevel
    urgency: Urgency
    assigned_department_id: Optional[str] = None
    assigned_reviewer_role: Optional[str] = None
    current_prompt_version: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    files: List[DocumentFileOut] = []
    artifacts: List[ExtractedArtifactOut] = []
    analyses: List[AIAnalysisOut] = []
    routing_decisions: List[RoutingDecisionOut] = []
    consultation_notes: List[ConsultationNoteOut] = []
    audit_events: List[AuditEventOut] = []

    model_config = ConfigDict(from_attributes=True)
