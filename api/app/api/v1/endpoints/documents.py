from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api import deps
from app.api.deps import CurrentRole
from app.models.document import AIAnalysis, AnalysisStage, AnalysisSource, DocumentStatus
from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentOut, DocumentListOut, DocumentDetailOut, UploadResponse
from app.services.ai.interface import AIProviderInterface
from app.services.audit_service import write_audit_event
from app.services.extraction.interface import ExtractionProviderInterface
from app.services.intake_service import IntakeService
from app.services.file_validation import FileValidationError
from app.services.storage import LocalFileStorage

router = APIRouter()


@router.get("/", response_model=List[DocumentListOut])
def get_documents(
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(deps.get_db),
):
    repo = DocumentRepository(db)
    docs = repo.list(status=status, department_id=department_id, q=q)
    return docs


@router.post("/", response_model=UploadResponse)
async def create_document(
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    """Upload a document file: validate, store, extract text."""
    content = await file.read()
    filename = file.filename or "upload.bin"
    mime_type = file.content_type

    svc = IntakeService(db)
    try:
        result = svc.intake(filename, content, mime_type, role.id)
    except FileValidationError:
        raise  # handled by global exception handler in main.py
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "PERSISTENCE_FAILED", "message": str(e), "details": {}}},
        )

    doc = result["document"]
    artifact = result.get("artifact")

    # Refresh to get DB-populated defaults
    db.commit()
    db.refresh(doc)
    if artifact:
        db.refresh(artifact)

    return UploadResponse(
        document=doc,
        extracted_artifact=artifact,
        ai_analyses=[],
    )


@router.get("/{doc_id}", response_model=DocumentDetailOut)
def get_document(doc_id: str, db: Session = Depends(deps.get_db)):
    repo = DocumentRepository(db)
    doc = repo.get_with_relations(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/file")
def get_document_file(doc_id: str, db: Session = Depends(deps.get_db)):
    """Stream raw file from storage."""
    repo = DocumentRepository(db)
    doc = repo.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.files:
        raise HTTPException(status_code=404, detail="No file attached to document")

    doc_file = doc.files[0]
    storage = LocalFileStorage()
    try:
        content = storage.read(doc_file.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in storage")

    return Response(
        content=content,
        media_type=doc_file.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc_file.original_filename}"'},
    )


@router.post("/{doc_id}/analyze", response_model=DocumentDetailOut)
async def analyze_document(
    doc_id: str,
    db: Session = Depends(deps.get_db),
    ai: AIProviderInterface = Depends(deps.get_ai_provider),
    role: CurrentRole = Depends(deps.get_current_role),
):
    from app.repositories import document as doc_repo

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

    repo = DocumentRepository(db)
    return repo.get_with_relations(doc_id)
