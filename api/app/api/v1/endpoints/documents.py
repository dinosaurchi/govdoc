from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api import deps
from app.api.deps import CurrentRole
from app.models.document import AIAnalysis, AnalysisStage, AnalysisSource, DocumentStatus
from app.repositories import document as doc_repo
from app.schemas.document import DocumentCreate, DocumentOut
from app.services.ai.interface import AIProviderInterface
from app.services.audit_service import write_audit_event
from app.services.extraction.interface import ExtractionProviderInterface
from app.services.intake_service import process_document_upload

router = APIRouter()


@router.get("/", response_model=List[DocumentOut])
def get_documents(db: Session = Depends(deps.get_db)):
    return doc_repo.document.get_multi(db, limit=200)


@router.post("/", response_model=DocumentOut)
async def create_document(
    obj_in: DocumentCreate,
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    doc = doc_repo.document.create(db, obj_in=obj_in)
    write_audit_event(
        db,
        document_id=doc.id,
        actor_role=role.id,
        event_type="DOCUMENT_CREATE_JSON",
        metadata_json={"title": doc.title},
    )
    db.commit()
    return doc_repo.document.get_with_relations(db, id=doc.id)


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
    extractor: ExtractionProviderInterface = Depends(deps.get_extraction_provider),
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
):
    doc = await process_document_upload(
        db,
        upload=file,
        title=title,
        role_id=role.id,
        extractor=extractor,
    )
    return doc_repo.document.get_with_relations(db, id=doc.id)


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db: Session = Depends(deps.get_db)):
    doc = doc_repo.document.get_with_relations(db, id=doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/{doc_id}/analyze", response_model=DocumentOut)
async def analyze_document(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    ai: AIProviderInterface = Depends(deps.get_ai_provider),
    role: CurrentRole = Depends(deps.get_current_role),
):
    doc = doc_repo.document.get_with_relations(db, id=doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.analyses:
        raise HTTPException(
            status_code=409,
            detail="This document already has an AI analysis record; re-run is not supported in baseline",
        )

    analysis_data = await ai.analyze_document("Mock context for doc")

    analysis_obj = AIAnalysis(
        document_id=doc.id,
        stage=AnalysisStage.classify,
        model_name=getattr(ai, "source_label", None) or type(ai).__name__,
        prompt_version="baseline",
        source=AnalysisSource.live,
        payload_json=analysis_data,
    )
    db.add(analysis_obj)

    doc.status = DocumentStatus.analyzed
    db.add(doc)

    write_audit_event(
        db,
        document_id=doc.id,
        actor_role=role.id,
        event_type="ANALYZE",
        metadata_json={
            "analysis_source": analysis_obj.model_name,
        },
    )

    db.commit()
    db.refresh(doc)

    return doc_repo.document.get_with_relations(db, id=doc_id)
