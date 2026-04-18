from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api import deps
from app.api.deps import CurrentRole
from app.models.document import Document, ExtractedArtifact
from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentListOut, DocumentDetailOut, UploadResponse
from app.services.ai.interface import AIProvider
from app.services.intake_service import IntakeService
from app.services.file_validation import FileValidationError
from app.services.storage import LocalFileStorage

router = APIRouter()


@router.get("/", response_model=List[DocumentListOut])
def get_documents(
    response: Response,
    status: Optional[str] = None,
    department_id: Optional[str] = None,
    q: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
):
    repo = DocumentRepository(db)
    total = repo.count(status=status, department_id=department_id, q=q)
    docs = repo.list(
        status=status,
        department_id=department_id,
        q=q,
        offset=offset,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return docs


@router.post("/", response_model=UploadResponse)
async def create_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.get_current_role),
    ai_provider: AIProvider = Depends(deps.get_ai_provider),
):
    """Upload a document file: validate, store, extract text, run AI analysis."""
    content = await file.read()
    filename = file.filename or "upload.bin"
    mime_type = file.content_type

    prompt_registry = getattr(request.app.state, "prompt_registry", None)

    svc = IntakeService(db)
    try:
        result = svc.intake(
            filename, content, mime_type, role.id,
            ai_provider=ai_provider, prompt_registry=prompt_registry,
        )
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
def get_document(doc_id: str, db: Session = Depends(deps.get_db), role: CurrentRole = Depends(deps.get_current_role)):
    from app.models.document import DocumentStatus
    from app.services.audit_service import write_audit_event

    repo = DocumentRepository(db)
    doc = repo.get_with_relations(doc_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    # Implicit transition: reviewer/supervisor reading a `routed` doc claims it → under_review
    # (per implementation plan §3.4: "reviewer opens record (implicit on read by reviewer role)")
    if doc.status == DocumentStatus.routed and role.has_action("documents.approve_routing"):
        doc.status = DocumentStatus.under_review
        if not doc.assigned_reviewer_role:
            doc.assigned_reviewer_role = role.id
        write_audit_event(
            db,
            document_id=doc.id,
            actor_role=role.id,
            event_type="workflow.transition",
            from_state="routed",
            to_state="under_review",
        )
        db.commit()
        db.refresh(doc)

    return doc


@router.get("/{doc_id}/file")
def get_document_file(
    doc_id: str, db: Session = Depends(deps.get_db), role: CurrentRole = Depends(deps.get_current_role)
):
    """Stream raw file from storage."""
    repo = DocumentRepository(db)
    doc = repo.get(doc_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )
    if not doc.files:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "No file attached to document", "details": {}}},
        )

    doc_file = doc.files[0]
    storage = LocalFileStorage()
    try:
        content = storage.read(doc_file.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "File not found in storage", "details": {}}},
        )

    return Response(
        content=content,
        media_type=doc_file.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc_file.original_filename}"'},
    )


@router.post("/{doc_id}/analyze")
async def re_analyze_document(
    doc_id: str,
    request: Request,
    force: bool = Query(False),
    db: Session = Depends(deps.get_db),
    role: CurrentRole = Depends(deps.require_action("documents.analyze")),
    ai_provider: AIProvider = Depends(deps.get_ai_provider),
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

    prompt_registry = getattr(request.app.state, "prompt_registry", None)
    analysis_svc = AnalysisService(db, ai_provider, prompt_registry=prompt_registry)

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


@router.get("/{document_id}/evidence")
async def get_document_evidence(
    document_id: str,
    role: CurrentRole = Depends(deps.get_current_role),
    db: Session = Depends(deps.get_db),
):
    """Get evidence/references for an analyzed document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    # Get text from latest artifact
    artifact = (
        db.query(ExtractedArtifact)
        .filter(ExtractedArtifact.document_id == document_id)
        .order_by(ExtractedArtifact.extracted_at.desc())
        .first()
    )

    if not artifact:
        return {"results": []}

    from app.main import app

    retrieval_svc = getattr(app.state, "retrieval_service", None)
    if not retrieval_svc:
        return {"results": []}

    results = retrieval_svc.search(artifact.text[:2000], top_k=5)
    return {"document_id": document_id, "results": results}
