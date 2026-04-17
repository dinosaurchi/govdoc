from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.models.document import WorkflowState, DocumentType

class DocumentBase(BaseModel):
    title: str
    doc_type: DocumentType

class DocumentCreate(DocumentBase):
    pass

class AIAnalysisOut(BaseModel):
    suggested_type: str
    urgency_score: int
    summary: str
    suggested_department: str

class RoutingDecisionOut(BaseModel):
    id: int
    assigned_by_id: int
    target_department_id: int
    note: Optional[str] = None
    created_at: datetime

class ConsultationNoteOut(BaseModel):
    id: int
    author_role_id: int
    content: str
    created_at: datetime

class DocumentOut(DocumentBase):
    id: int
    state: WorkflowState
    created_at: datetime
    updated_at: datetime
    analysis: Optional[AIAnalysisOut] = None
    decisions: List[RoutingDecisionOut] = []
    consultations: List[ConsultationNoteOut] = []

    model_config = ConfigDict(from_attributes=True)
