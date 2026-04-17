from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.repositories.base import CRUDBase
from app.models.document import Document, DocumentFile, RoutingDecision, ConsultationNote
from app.schemas.document import DocumentCreate
from pydantic import BaseModel


class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Document:
        doc = Document(**kwargs)
        self.db.add(doc)
        self.db.flush()
        return doc

    def get(self, document_id: str) -> Document | None:
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_with_relations(self, document_id: str) -> Document | None:
        return (
            self.db.query(Document)
            .options(
                joinedload(Document.files),
                joinedload(Document.artifacts),
                joinedload(Document.analyses),
                joinedload(Document.routing_decisions),
                joinedload(Document.consultation_notes),
                joinedload(Document.audit_events),
            )
            .filter(Document.id == document_id)
            .first()
        )

    def _list_query(
        self,
        status: str | None = None,
        department_id: str | None = None,
        q: str | None = None,
    ):
        query = self.db.query(Document)
        if status:
            query = query.filter(Document.status == status)
        if department_id:
            query = query.filter(Document.assigned_department_id == department_id)
        if q:
            query = query.filter(Document.title.ilike(f"%{q}%"))
        return query

    def list(
        self,
        status: str | None = None,
        department_id: str | None = None,
        q: str | None = None,
        offset: int = 0,
        limit: int = 200,
    ) -> list[Document]:
        return (
            self._list_query(status=status, department_id=department_id, q=q)
            .order_by(Document.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count(
        self,
        status: str | None = None,
        department_id: str | None = None,
        q: str | None = None,
    ) -> int:
        return self._list_query(
            status=status, department_id=department_id, q=q
        ).count()

    def update(self, document: Document, **kwargs) -> Document:
        for key, value in kwargs.items():
            setattr(document, key, value)
        self.db.flush()
        return document


# Legacy CRUDBase instances — kept for backward compat with workflow.py and __init__.py
class CRUDDocument(CRUDBase[Document, DocumentCreate, BaseModel]):
    def get_with_relations(self, db: Session, *, id: Any) -> Document | None:
        return (
            db.query(Document)
            .options(
                joinedload(Document.files),
                joinedload(Document.artifacts),
                joinedload(Document.analyses),
                joinedload(Document.routing_decisions),
                joinedload(Document.consultation_notes),
                joinedload(Document.audit_events),
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
