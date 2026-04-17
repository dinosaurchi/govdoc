from app.repositories import document as doc_repo
from app.repositories import system as sys_repo
from app.models.document import WorkflowState, Document
from sqlalchemy.orm import Session
from fastapi import HTTPException

class WorkflowService:
    def __init__(self, db: Session):
        self.db = db

    def _validate_transition(self, current_state: WorkflowState, next_state: WorkflowState):
        # Implementation of Vietnam Gov public sector workflow rules
        allowed_transitions = {
            WorkflowState.intake_received: [WorkflowState.registered, WorkflowState.archived_demo_only],
            WorkflowState.registered: [WorkflowState.routed_pending_human_review, WorkflowState.assigned_to_department],
            WorkflowState.routed_pending_human_review: [WorkflowState.assigned_to_department, WorkflowState.registered],
            WorkflowState.assigned_to_department: [WorkflowState.under_review],
            WorkflowState.under_review: [WorkflowState.consultation_requested, WorkflowState.response_prepared],
            WorkflowState.consultation_requested: [WorkflowState.consultation_completed],
            WorkflowState.consultation_completed: [WorkflowState.under_review, WorkflowState.response_prepared],
            WorkflowState.response_prepared: [WorkflowState.closed, WorkflowState.under_review],
            WorkflowState.closed: [WorkflowState.archived_demo_only],
            WorkflowState.archived_demo_only: []
        }
        
        if next_state not in allowed_transitions.get(current_state, []):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid state transition from {current_state} to {next_state}"
            )

    async def transition_state(self, document_id: int, next_state: WorkflowState, actor_role_id: int):
        doc = doc_repo.document.get(self.db, id=document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
            
        old_state = doc.state
        self._validate_transition(old_state, next_state)
        
        doc.state = next_state
        self.db.add(doc)
        
        # Log Audit Event
        sys_repo.audit_event.create(self.db, obj_in={
            "document_id": document_id,
            "actor_role_id": actor_role_id,
            "action": f"TRANSITION",
            "details": {"old_state": old_state, "new_state": next_state}
        })
        self.db.commit()
        return doc

    async def add_consultation(self, document_id: int, author_role_id: int, content: str):
        doc = doc_repo.document.get(self.db, id=document_id)
        if not doc:
             raise HTTPException(status_code=404, detail="Document not found")
        
        note = doc_repo.consultation_note.create(self.db, obj_in={
            "document_id": document_id,
            "author_role_id": author_role_id,
            "content": content
        })
        
        # Auto-transition to consultation_requested if in under_review
        if doc.state == WorkflowState.under_review:
            await self.transition_state(document_id, WorkflowState.consultation_requested, author_role_id)
            
        return note

    async def create_routing_decision(self, document_id: int, assigned_by_id: int, target_dept_id: int, note: str):
        decision = doc_repo.routing_decision.create(self.db, obj_in={
            "document_id": document_id,
            "assigned_by_id": assigned_by_id,
            "target_department_id": target_dept_id,
            "note": note
        })
        return decision
