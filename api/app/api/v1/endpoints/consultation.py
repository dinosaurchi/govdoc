from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps import CurrentRole
from app.services.workflow import WorkflowService

router = APIRouter()


class ConsultationNoteBody(BaseModel):
    content: str = Field(..., min_length=1)


@router.get("/")
async def list_active_consultations(db: Session = Depends(deps.get_db)):
    return []


@router.post("/{doc_id}/notes")
async def add_consultation_note(
    doc_id: str,
    body: ConsultationNoteBody,
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    if role.id not in ["reviewer", "consultant", "supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to add consultation notes")

    workflow = WorkflowService(db)
    return await workflow.add_consultation(doc_id, role.id, body.content)


@router.post("/{doc_id}/complete")
async def complete_consultation(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    if role.id not in ["consultant", "reviewer", "supervisor"]:
        raise HTTPException(status_code=403, detail="Not authorized to complete consultation")

    workflow = WorkflowService(db)
    return await workflow.complete_consultation(doc_id, role.id)
