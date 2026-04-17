from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.api.role_util import get_role_id_by_name
from app.models.document import DocumentStatus
from app.services.workflow import WorkflowService

router = APIRouter()


@router.post("/{doc_id}/route")
async def route_document(
    doc_id: str,
    target_dept_id: str,
    note: str = "",
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role),
):
    if role not in ["Intake Clerk", "Department Reviewer", "Supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to route documents")

    actor_id = get_role_id_by_name(db, role)
    workflow = WorkflowService(db)
    return await workflow.create_routing_decision(
        doc_id, actor_id, target_dept_id, target_dept_id, "accepted", note or None
    )


@router.post("/{doc_id}/start-review")
async def start_department_review(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role),
):
    if role not in ["Department Reviewer", "Consultant", "Supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to start department review")

    actor_id = get_role_id_by_name(db, role)
    workflow = WorkflowService(db)
    return await workflow.transition_state(
        doc_id,
        DocumentStatus.under_review,
        actor_id,
        event_type="REVIEW_STARTED",
    )


@router.post("/{doc_id}/prepare-response")
async def prepare_response(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role),
):
    if role not in ["Department Reviewer", "Supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to prepare response")

    actor_id = get_role_id_by_name(db, role)
    workflow = WorkflowService(db)
    return await workflow.transition_state(
        doc_id,
        DocumentStatus.approved,
        actor_id,
        event_type="RESPONSE_PREPARED",
    )


@router.post("/{doc_id}/approve")
async def approve_document(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role),
):
    if role not in ["Supervisor"]:
        raise HTTPException(status_code=403, detail="Only supervisors can approve final dispatch")

    actor_id = get_role_id_by_name(db, role)
    workflow = WorkflowService(db)
    return await workflow.transition_state(
        doc_id,
        DocumentStatus.closed,
        actor_id,
        event_type="CLOSE_APPROVED",
    )
