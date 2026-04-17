from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps import CurrentRole
from app.models.document import DocumentStatus
from app.services.workflow import WorkflowService

router = APIRouter()


@router.post("/{doc_id}/route")
async def route_document(
    doc_id: str,
    target_dept_id: str,
    note: str = "",
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    if role.id not in ["intake_clerk", "reviewer", "supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to route documents")

    workflow = WorkflowService(db)
    return await workflow.create_routing_decision(
        doc_id, role.id, target_dept_id, target_dept_id, "accepted", note or None
    )


@router.post("/{doc_id}/start-review")
async def start_department_review(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    if role.id not in ["reviewer", "consultant", "supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to start department review")

    workflow = WorkflowService(db)
    return await workflow.transition_state(
        doc_id,
        DocumentStatus.under_review,
        role.id,
        event_type="REVIEW_STARTED",
    )


@router.post("/{doc_id}/prepare-response")
async def prepare_response(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    if role.id not in ["reviewer", "supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to prepare response")

    workflow = WorkflowService(db)
    return await workflow.transition_state(
        doc_id,
        DocumentStatus.approved,
        role.id,
        event_type="RESPONSE_PREPARED",
    )


@router.post("/{doc_id}/approve")
async def approve_document(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    if role.id not in ["supervisor"]:
        raise HTTPException(status_code=403, detail="Only supervisors can approve final dispatch")

    workflow = WorkflowService(db)
    return await workflow.transition_state(
        doc_id,
        DocumentStatus.closed,
        role.id,
        event_type="CLOSE_APPROVED",
    )
