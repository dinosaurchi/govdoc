from app.repositories.base import CRUDBase
from app.models.document import Document, DocumentFile, ExtractedArtifact, AIAnalysis, RoutingDecision, ConsultationNote
from app.schemas.document import DocumentCreate
from pydantic import BaseModel

class CRUDDocument(CRUDBase[Document, DocumentCreate, BaseModel]):
    pass

class CRUDDocumentFile(CRUDBase[DocumentFile, BaseModel, BaseModel]):
    pass

class CRUDRoutingDecision(CRUDBase[RoutingDecision, BaseModel, BaseModel]):
    pass

class CRUDConsultationNote(CRUDBase[ConsultationNote, BaseModel, BaseModel]):
    pass

document = CRUDDocument(Document)
document_file = CRUDDocumentFile(DocumentFile)
routing_decision = CRUDRoutingDecision(RoutingDecision)
consultation_note = CRUDConsultationNote(ConsultationNote)
