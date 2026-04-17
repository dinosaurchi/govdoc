from app.repositories import document as doc_repo
from app.models.document import WorkflowState
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.audit_service import write_audit_event


class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def ensure_transition_allowed(self, current_state: WorkflowState, next_state: WorkflowState) -> None:
        """Public guard for endpoints that mutate state alongside other persistence."""
        self._validate_transition(current_state, next_state)

    def _validate_transition(self, current_state: WorkflowState, next_state: WorkflowState):
        allowed_transitions = {
            WorkflowState.intake_received: [
                WorkflowState.registered,
                WorkflowState.routed_pending_human_review,
                WorkflowState.archived_demo_only,
            ],
            WorkflowState.registered: [
                WorkflowState.routed_pending_human_review,
                WorkflowState.assigned_to_department,
            ],
            WorkflowState.routed_pending_human_review: [
                WorkflowState.assigned_to_department,
                WorkflowState.registered,
            ],
            WorkflowState.assigned_to_department: [WorkflowState.under_review],
            WorkflowState.under_review: [
                WorkflowState.consultation_requested,
                WorkflowState.response_prepared,
            ],
            WorkflowState.consultation_requested: [
                WorkflowState.consultation_completed,
                WorkflowState.under_review,
            ],
            WorkflowState.consultation_completed: [
                WorkflowState.under_review,
                WorkflowState.response_prepared,
            ],
            WorkflowState.response_prepared: [WorkflowState.closed, WorkflowState.under_review],
            WorkflowState.closed: [WorkflowState.archived_demo_only],
            WorkflowState.archived_demo_only: [],
        }

        if next_state not in allowed_transitions.get(current_state, []):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state transition from {current_state.value} to {next_state.value}",
            )

    async def transition_state(
        self,
        document_id: int,
        next_state: WorkflowState,
        actor_role_id: int,
        *,
        action: str = "WORKFLOW_TRANSITION",
        extra_details: dict | None = None,
    ):
        doc = doc_repo.document.get(self.db, id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        old_state = doc.state
        self._validate_transition(old_state, next_state)

        doc.state = next_state
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)

        details = {"old_state": old_state.value, "new_state": next_state.value}
        if extra_details:
            details.update(extra_details)

        write_audit_event(
            self.db,
            document_id=document_id,
            actor_role_id=actor_role_id,
            action=action,
            details=details,
        )
        return doc

    async def add_consultation(self, document_id: int, author_role_id: int, content: str):
        doc = doc_repo.document.get(self.db, id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        note = doc_repo.consultation_note.create(
            self.db,
            obj_in={
                "document_id": document_id,
                "author_role_id": author_role_id,
                "content": content,
            },
        )

        write_audit_event(
            self.db,
            document_id=document_id,
            actor_role_id=author_role_id,
            action="CONSULTATION_NOTE_CREATED",
            details={"note_id": note.id},
        )

        doc = doc_repo.document.get(self.db, id=document_id)
        if doc and doc.state == WorkflowState.under_review:
            await self.transition_state(
                document_id,
                WorkflowState.consultation_requested,
                author_role_id,
                action="CONSULTATION_REQUESTED",
            )

        return note

    async def complete_consultation(self, document_id: int, actor_role_id: int):
        return await self.transition_state(
            document_id,
            WorkflowState.consultation_completed,
            actor_role_id,
            action="CONSULTATION_COMPLETED",
        )

    async def create_routing_decision(
        self, document_id: int, assigned_by_id: int, target_dept_id: int, note: str
    ):
        doc = doc_repo.document.get(self.db, id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        decision = doc_repo.routing_decision.create(
            self.db,
            obj_in={
                "document_id": document_id,
                "assigned_by_id": assigned_by_id,
                "target_department_id": target_dept_id,
                "note": note or None,
            },
        )

        write_audit_event(
            self.db,
            document_id=document_id,
            actor_role_id=assigned_by_id,
            action="ROUTE",
            details={
                "routing_decision_id": decision.id,
                "target_department_id": target_dept_id,
                "note": note or "",
            },
        )

        await self.transition_state(
            document_id,
            WorkflowState.assigned_to_department,
            assigned_by_id,
            action="ROUTE_APPROVED",
            extra_details={"routing_decision_id": decision.id},
        )

        return decision
