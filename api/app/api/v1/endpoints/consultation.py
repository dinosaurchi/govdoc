from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.services.workflow import WorkflowService
from typing import List

router = APIRouter()

@router.get("/")
async def list_active_consultations(db: Session = Depends(deps.get_db)):
    # Placeholder search
    return []

@router.post("/{doc_id}/notes")
async def add_consultation_note(
    doc_id: int,
    content: str,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role)
):
    workflow = WorkflowService(db)
    return await workflow.add_consultation(doc_id, 1, content)
