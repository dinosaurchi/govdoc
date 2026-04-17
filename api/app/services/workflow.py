from typing import Any

from app.repositories import document as doc_repo
from app.models.document import DocumentStatus
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.audit_service import write_audit_event


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_transition_allowed(self, current_status: DocumentStatus, next_status: DocumentStatus) -> None:
        """Public guard for endpoints that mutate state alongside other persistence."""
        self._validate_transition(current_status, next_status)

    def _validate_transition(self, current_status: DocumentStatus, next_status: DocumentStatus):
        allowed_transitions = {
            DocumentStatus.received: [
                DocumentStatus.extracted,
                DocumentStatus.ingest_failed,
            ],
            DocumentStatus.extracted: [
                DocumentStatus.analyzed,
                DocumentStatus.ingest_failed,
            ],
            DocumentStatus.analyzed: [
                DocumentStatus.routed,
                DocumentStatus.analysis_failed,
            ],
            DocumentStatus.routed: [
                DocumentStatus.under_review,
                DocumentStatus.out_of_scope,
            ],
            DocumentStatus.under_review: [
                DocumentStatus.in_consultation,
                DocumentStatus.approved,
            ],
            DocumentStatus.in_consultation: [
                DocumentStatus.under_review,
                DocumentStatus.approved,
            ],
            DocumentStatus.approved: [DocumentStatus.closed],
            DocumentStatus.closed: [],
            DocumentStatus.out_of_scope: [],
            DocumentStatus.ingest_failed: [],
            DocumentStatus.analysis_failed: [],
        }

        if next_status not in allowed_transitions.get(current_status, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state transition from {current_status.value} to {next_status.value}",
            )

    async def transition_state(
        self,
        document_id: str,
        next_status: DocumentStatus,
        actor_role: str,
        *,
        event_type: str = "WORKFLOW_TRANSITION",
        metadata_json: dict[str, Any] | None = None,
    ):
        doc = doc_repo.document.get(self.db, id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        old_status = doc.status
        self._validate_transition(old_status, next_status)

        doc.status = next_status
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        meta: dict[str, Any] = {"old_status": old_status.value, "new_status": next_status.value}
        if metadata_json:
            meta.update(metadata_json)

        write_audit_event(
            self.db,
            document_id=document_id,
            actor_role=actor_role,
            event_type=event_type,
            from_state=old_status.value,
            to_state=next_status.value,
            metadata_json=meta,
        )
        return doc

    async def add_consultation(self, document_id: str, author_role: str, body: str):
        doc = doc_repo.document.get(self.db, id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        note = doc_repo.consultation_note.create(
            self.db,
            obj_in={
                "document_id": document_id,
                "author_role": author_role,
                "body": body,
            },
        )

        write_audit_event(
            self.db,
            document_id=document_id,
            actor_role=author_role,
            event_type="CONSULTATION_NOTE_CREATED",
            metadata_json={"note_id": note.id},
        )

        doc = doc_repo.document.get(self.db, id=document_id)
        if doc and doc.status == DocumentStatus.under_review:
            await self.transition_state(
                document_id,
                DocumentStatus.in_consultation,
                author_role,
                event_type="CONSULTATION_REQUESTED",
            )

        return note

    async def complete_consultation(self, document_id: str, actor_role: str):
        return await self.transition_state(
            document_id,
            DocumentStatus.under_review,
            actor_role,
            event_type="CONSULTATION_COMPLETED",
        )

    async def create_routing_decision(
        self,
        document_id: str,
        decided_by_role: str,
        suggested_department_id: str | None,
        final_department_id: str | None,
        decision: str,
        rationale: str | None = None,
    ):
        doc = doc_repo.document.get(self.db, id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        routing_decision = doc_repo.routing_decision.create(
            self.db,
            obj_in={
                "document_id": document_id,
                "decided_by_role": decided_by_role,
                "suggested_department_id": suggested_department_id,
                "final_department_id": final_department_id,
                "decision": decision,
                "rationale": rationale,
            },
        )

        write_audit_event(
            self.db,
            document_id=document_id,
            actor_role=decided_by_role,
            event_type="ROUTE",
            metadata_json={
                "routing_decision_id": routing_decision.id,
                "suggested_department_id": suggested_department_id,
                "rationale": rationale or "",
            },
        )

        return routing_decision
