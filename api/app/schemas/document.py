from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional, Any

from app.models.document import WorkflowState, DocumentType


class DocumentBase(BaseModel):
    title: str
    doc_type: DocumentType


class DocumentCreate(DocumentBase):
    pass


class DocumentFileOut(BaseModel):
    id: int
    file_name: str
    mime_type: str
    file_size_bytes: int
    storage_relative_path: str
    sha256_hex: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractedArtifactOut(BaseModel):
    id: int
    extraction_method: str
    extraction_source_label: str
    extracted_text: str
    structured_metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIAnalysisOut(BaseModel):
    suggested_type: str
    urgency_score: int
    summary: str
    suggested_department: str
    analysis_source_label: str

    model_config = ConfigDict(from_attributes=True)


class RoutingDecisionOut(BaseModel):
    id: int
    assigned_by_id: int
    target_department_id: int
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsultationNoteOut(BaseModel):
    id: int
    author_role_id: int
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditEventOut(BaseModel):
    id: int
    actor_role_id: int
    action: str
    details: Optional[dict[str, Any]] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentOut(DocumentBase):
    id: int
    state: WorkflowState
    created_at: datetime
    updated_at: datetime
    files: List[DocumentFileOut] = []
    artifacts: List[ExtractedArtifactOut] = []
    analysis: Optional[AIAnalysisOut] = None
    decisions: List[RoutingDecisionOut] = []
    consultations: List[ConsultationNoteOut] = []
    audit_logs: List[AuditEventOut] = []

    model_config = ConfigDict(from_attributes=True)
