from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.services.workflow import WorkflowService
from app.models.document import WorkflowState

router = APIRouter()

@router.post("/{doc_id}/route")
async def route_document(
    doc_id: int, 
    target_dept_id: int,
    note: str = "",
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role)
):
    # Simulation: only clerks or reviewers can route
    if role not in ["Intake Clerk", "Department Reviewer", "Supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to route documents")
    
    workflow = WorkflowService(db)
    # Mocking role ID for now
    actor_id = 1 
    await workflow.create_routing_decision(doc_id, actor_id, target_dept_id, note)
    return await workflow.transition_state(doc_id, WorkflowState.assigned_to_department, actor_id)

@router.post("/{doc_id}/approve")
async def approve_document(
    doc_id: int,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role)
):
    if role not in ["Supervisor"]:
        raise HTTPException(status_code=403, detail="Only supervisors can approve final dispatch")
    
    workflow = WorkflowService(db)
    return await workflow.transition_state(doc_id, WorkflowState.closed, 1)
