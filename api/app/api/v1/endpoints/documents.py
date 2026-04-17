from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api import deps
from app.api.role_util import get_role_id_by_name
from app.models.document import AIAnalysis, DocumentType, WorkflowState
from app.repositories import document as doc_repo
from app.schemas.document import DocumentCreate, DocumentOut
from app.services.ai.interface import AIProviderInterface
from app.services.audit_service import write_audit_event
from app.services.extraction.interface import ExtractionProviderInterface
from app.services.intake_service import process_document_upload
from app.services.workflow import WorkflowService

router = APIRouter()


def _parse_doc_type(raw: Optional[str]) -> DocumentType:
    if not raw:
        return DocumentType.cong_van
    mapping = {
        "công văn": DocumentType.cong_van,
        "quyết định": DocumentType.quyet_dinh,
        "thông báo": DocumentType.thong_bao,
        "tờ trình": DocumentType.to_trinh,
        "báo cáo": DocumentType.bao_cao,
        "cong_van": DocumentType.cong_van,
        "quyet_dinh": DocumentType.quyet_dinh,
        "thong_bao": DocumentType.thong_bao,
        "to_trinh": DocumentType.to_trinh,
        "bao_cao": DocumentType.bao_cao,
    }
    key = raw.strip().lower()
    if key in mapping:
        return mapping[key]
    try:
        return DocumentType(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid doc_type: {raw}")


@router.get("/", response_model=List[DocumentOut])
def get_documents(db: Session = Depends(deps.get_db)):
    return doc_repo.document.get_multi(db, limit=200)


@router.post("/", response_model=DocumentOut)
async def create_document(
    obj_in: DocumentCreate,
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role),
):
    actor_id = get_role_id_by_name(db, role)
    doc = doc_repo.document.create(db, obj_in=obj_in)
    write_audit_event(
        db,
        document_id=doc.id,
        actor_role_id=actor_id,
        action="DOCUMENT_CREATE_JSON",
        details={"title": doc.title},
    )
    return doc_repo.document.get_with_relations(db, id=doc.id)


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    db: Session = Depends(deps.get_db),
    role: str = Depends(deps.get_current_role),
    extractor: ExtractionProviderInterface = Depends(deps.get_extraction_provider),
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    doc_type: Optional[str] = Form(None),
):
    dt = _parse_doc_type(doc_type)
    doc = await process_document_upload(
        db,
        upload=file,
        title=title,
        doc_type=dt,
        role_name=role,
        extractor=extractor,
    )
    return doc_repo.document.get_with_relations(db, id=doc.id)


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: int, db: Session = Depends(deps.get_db)):
    doc = doc_repo.document.get_with_relations(db, id=doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/{doc_id}/analyze", response_model=DocumentOut)
async def analyze_document(
    doc_id: int,
    db: Session = Depends(deps.get_db),
    ai: AIProviderInterface = Depends(deps.get_ai_provider),
    role: str = Depends(deps.get_current_role),
):
    doc = doc_repo.document.get_with_relations(db, id=doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.analysis is not None:
        raise HTTPException(
            status_code=409,
            detail="This document already has an AI analysis record; re-run is not supported in baseline",
        )

    wf = WorkflowService(db)
    wf.ensure_transition_allowed(doc.state, WorkflowState.routed_pending_human_review)

    analysis_data = await ai.analyze_document("Mock context for doc")

    actor_id = get_role_id_by_name(db, role)

    analysis_obj = AIAnalysis(
        document_id=doc.id,
        suggested_type=analysis_data["suggested_type"],
        urgency_score=analysis_data["urgency_score"],
        summary=analysis_data["summary"],
        suggested_department=analysis_data["suggested_department"],
        raw_response='{"mock": true}',
        analysis_source_label=getattr(ai, "source_label", None) or type(ai).__name__,
    )
    db.add(analysis_obj)

    doc.state = WorkflowState.routed_pending_human_review
    db.add(doc)
    db.commit()
    db.refresh(doc)

    write_audit_event(
        db,
        document_id=doc.id,
        actor_role_id=actor_id,
        action="ANALYZE",
        details={
            "suggested_department": analysis_data.get("suggested_department"),
            "analysis_source": analysis_obj.analysis_source_label,
        },
    )

    return doc_repo.document.get_with_relations(db, id=doc_id)
