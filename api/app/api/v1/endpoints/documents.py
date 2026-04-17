from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api import deps
from app.api.deps import CurrentRole
from app.models.document import Document, DocumentStatus
from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentOut, DocumentListOut, DocumentDetailOut, UploadResponse
from app.services.ai.interface import AIProvider
from app.services.ai.mock_provider import MockAIProvider
from app.services.audit_service import write_audit_event
from app.services.extraction.interface import ExtractionProviderInterface
from app.services.intake_service import IntakeService
from app.services.file_validation import FileValidationError
from app.services.storage import LocalFileStorage

router = APIRouter()


def _get_ai_provider() -> AIProvider:
    """Try real provider; fall back to mock if credentials not configured."""
    try:
        from app.services.ai.real_provider import RealAIProvider

        return RealAIProvider()
    except Exception:
        return MockAIProvider()


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
    """Upload a document file: validate, store, extract text, run AI analysis."""
    content = await file.read()
    filename = file.filename or "upload.bin"
    mime_type = file.content_type

    # Determine AI provider (real if credentials available, mock otherwise)
    ai_provider = _get_ai_provider()

    svc = IntakeService(db)
    try:
        result = svc.intake(filename, content, mime_type, role.id, ai_provider=ai_provider)
    except FileValidationError:
        raise  # handled by global exception handler in main.py
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "PERSISTENCE_FAILED", "message": str(e), "details": {}}},
        )

    doc = result["document"]
    artifact = result.get("artifact")
    ai_analyses = result.get("ai_analyses", [])

    # Refresh to get DB-populated defaults
    db.commit()
    db.refresh(doc)
    if artifact:
        db.refresh(artifact)

    # Refresh analysis objects so created_at etc. are populated
    refreshed_analyses = []
    for a in ai_analyses:
        db.refresh(a)
        refreshed_analyses.append(a)

    return UploadResponse(
        document=doc,
        extracted_artifact=artifact,
        ai_analyses=refreshed_analyses,
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


@router.post("/{doc_id}/analyze")
async def re_analyze_document(
    doc_id: str,
    force: bool = Query(False),
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.require_action("documents.analyze")),
):
    """Re-run AI analysis on a document (classify → summarize → route → optional escalate)."""
    from app.services.ai.analysis_service import AnalysisService

    repo = DocumentRepository(db)
    document = repo.get_with_relations(doc_id)
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    ai_provider = _get_ai_provider()
    analysis_svc = AnalysisService(db, ai_provider)

    try:
        analyses = analysis_svc.re_analyze(document, role.id, force=force)
        db.commit()
        # Refresh to populate relationships
        db.refresh(document)
        for a in analyses:
            db.refresh(a)
        return {"document": document, "ai_analyses": analyses}
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "EXTRACTION_FAILED", "message": str(e), "details": {}}},
        )
