from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.api.role_util import get_role_id_by_name
from app.services.workflow import WorkflowService

router = APIRouter()


class ConsultationNoteBody(BaseModel):
    content: str = Field(..., min_length=1)


@router.get("/")
async def list_active_consultations(db: Session = Depends(deps.get_db)):
    return []


@router.post("/{doc_id}/notes")
async def add_consultation_note(
    doc_id: int,
    body: ConsultationNoteBody,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role),
):
    if role not in ["Department Reviewer", "Consultant", "Supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to add consultation notes")

    actor_id = get_role_id_by_name(db, role)
    workflow = WorkflowService(db)
    return await workflow.add_consultation(doc_id, actor_id, body.content)


@router.post("/{doc_id}/complete")
async def complete_consultation(
    doc_id: int,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role),
):
    if role not in ["Consultant", "Department Reviewer", "Supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to complete consultation")

    actor_id = get_role_id_by_name(db, role)
    workflow = WorkflowService(db)
    return await workflow.complete_consultation(doc_id, actor_id)
