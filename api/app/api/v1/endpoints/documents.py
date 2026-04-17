from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.api import deps
from app.repositories import document as doc_repo
from app.schemas.document import DocumentOut, DocumentCreate
from app.services.workflow import WorkflowService
from app.services.ai.interface import AIProviderInterface
from app.models.document import WorkflowState

router = APIRouter()

@router.get("/", response_model=List[DocumentOut])
def get_documents(db: Session = Depends(deps.get_db)):
    return doc_repo.document.get_multi(db, limit=100)

@router.post("/", response_model=DocumentOut)
async def create_document(
    obj_in: DocumentCreate,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role)
):
    doc = doc_repo.document.create(db, obj_in=obj_in)
    return doc

@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(deps.get_db)):
    doc = doc_repo.document.get(db, id=doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.post("/{doc_id}/analyze", response_model=DocumentOut)
async def analyze_document(
    doc_id: int,
    db: Session = Depends(deps.get_db),
    ai: AIProviderInterface = Depends(deps.get_ai_provider)
):
    doc = doc_repo.document.get(db, id=doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Real mock integration
    analysis_data = await ai.analyze_document("Mock context for doc")
    
    # Create Analysis Record
    from app.models.document import AIAnalysis
    analysis_obj = AIAnalysis(
        document_id=doc.id,
        suggested_type=analysis_data["suggested_type"],
        urgency_score=analysis_data["urgency_score"],
        summary=analysis_data["summary"],
        suggested_department=analysis_data["suggested_department"],
        raw_response="MOCK_JSON_PAYLOAD_HERE"
    )
    db.add(analysis_obj)
    
    # Update state to registered if it was intake_received
    if doc.state == WorkflowState.intake_received:
        doc.state = WorkflowState.registered
    
    db.commit()
    db.refresh(doc)
    return doc
