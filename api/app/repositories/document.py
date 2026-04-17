from sqlalchemy.orm import Session, joinedload

from app.repositories.base import CRUDBase
from app.models.document import Document, DocumentFile, RoutingDecision, ConsultationNote
from app.schemas.document import DocumentCreate
from pydantic import BaseModel


class CRUDDocument(CRUDBase[Document, DocumentCreate, BaseModel]):
    def get_with_relations(self, db: Session, *, id: int) -> Document | None:
        return (
            db.query(Document)
            .options(
                joinedload(Document.files),
                joinedload(Document.artifacts),
                joinedload(Document.analysis),
                joinedload(Document.decisions),
                joinedload(Document.consultations),
                joinedload(Document.audit_logs),
            )
            .filter(Document.id == id)
            .first()
        )

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
