from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, require_action, CurrentRole
from app.models.document import Document, DocumentStatus, RoutingDecision, ConsultationNote
from app.models.system import Department
from app.services.workflow import validate_transition, InvalidTransitionError
from app.services.audit_service import write_audit_event
from app.schemas.document import RoutingDecisionOut, ConsultationNoteOut, ConsultationRequest, RerouteRequest
import uuid

router = APIRouter(prefix="/documents", tags=["workflow"])


@router.post("/{document_id}/approve-routing")
async def approve_routing(
    document_id: str,
    role: CurrentRole = Depends(require_action("documents.approve_routing")),
    db: Session = Depends(get_db),
):
    """Approve routing — reviewer or supervisor."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    old_status = document.status.value
    try:
        validate_transition(document.status, DocumentStatus.routed)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e), "details": {}}},
        )

    document.status = DocumentStatus.routed
    document.assigned_reviewer_role = role.id
    write_audit_event(
        db,
        document_id=document_id,
        actor_role=role.id,
        event_type="workflow.transition",
        from_state=old_status,
        to_state="routed",
    )
    db.commit()
    return {"document": document, "message": "Routing approved"}


@router.post("/{document_id}/reroute")
async def reroute_document(
    document_id: str,
    body: RerouteRequest,
    role: CurrentRole = Depends(require_action("documents.reroute")),
    db: Session = Depends(get_db),
):
    """Reroute document to different department."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    # Validate department exists
    dept = db.query(Department).filter(Department.id == body.department_id).first()
    if not dept:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "NOT_FOUND", "message": "Department not found", "details": {}}},
        )

    old_status = document.status.value
    routing = RoutingDecision(
        id=str(uuid.uuid4()),
        document_id=document_id,
        suggested_department_id=body.department_id,
        final_department_id=body.department_id,
        decided_by_role=role.id,
        decision="rerouted",
        rationale=body.rationale,
    )
    db.add(routing)
    document.assigned_department_id = body.department_id
    document.status = DocumentStatus.routed
    write_audit_event(
        db,
        document_id=document_id,
        actor_role=role.id,
        event_type="workflow.transition",
        from_state=old_status,
        to_state="routed",
        metadata_json={"department_id": body.department_id},
    )
    db.commit()
    return {"document": document, "routing_decision": routing}


@router.post("/{document_id}/request-consultation")
async def request_consultation(
    document_id: str,
    body: ConsultationRequest,
    role: CurrentRole = Depends(require_action("documents.request_consultation")),
    db: Session = Depends(get_db),
):
    """Request consultation on a document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    old_status = document.status.value
    try:
        validate_transition(document.status, DocumentStatus.in_consultation)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e), "details": {}}},
        )

    note = ConsultationNote(
        id=str(uuid.uuid4()),
        document_id=document_id,
        author_role=role.id,
        target_role=body.target_role,
        body=body.body,
    )
    db.add(note)
    document.status = DocumentStatus.in_consultation
    write_audit_event(
        db,
        document_id=document_id,
        actor_role=role.id,
        event_type="workflow.transition",
        from_state=old_status,
        to_state="in_consultation",
    )
    db.commit()
    return {"document": document, "consultation_note": note}


@router.post("/{document_id}/resolve-consultation/{note_id}")
async def resolve_consultation(
    document_id: str,
    note_id: str,
    role: CurrentRole = Depends(require_action("documents.resolve_consultation")),
    db: Session = Depends(get_db),
):
    """Resolve a consultation note."""
    note = (
        db.query(ConsultationNote)
        .filter(
            ConsultationNote.id == note_id,
            ConsultationNote.document_id == document_id,
        )
        .first()
    )
    if not note:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Consultation note not found", "details": {}}},
        )

    if note.resolved_at:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TRANSITION", "message": "Note already resolved", "details": {}}},
        )

    note.resolved_at = func.now()
    document = db.query(Document).filter(Document.id == document_id).first()
    if document:
        old_status = document.status.value
        document.status = DocumentStatus.under_review
        write_audit_event(
            db,
            document_id=document_id,
            actor_role=role.id,
            event_type="workflow.transition",
            from_state=old_status,
            to_state="under_review",
        )
    db.commit()
    return {"document": document, "consultation_note": note}


@router.post("/{document_id}/escalate")
async def escalate_document(
    document_id: str,
    role: CurrentRole = Depends(require_action("documents.escalate")),
    db: Session = Depends(get_db),
):
    """Escalate document — supervisor only."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    write_audit_event(
        db,
        document_id=document_id,
        actor_role=role.id,
        event_type="workflow.escalate",
    )
    db.commit()
    return {"document": document, "message": "Document escalated for supervisor review"}


@router.post("/{document_id}/mark-out-of-scope")
async def mark_out_of_scope(
    document_id: str,
    role: CurrentRole = Depends(require_action("documents.mark_out_of_scope")),
    db: Session = Depends(get_db),
):
    """Mark document as out of scope."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    old_status = document.status.value
    document.status = DocumentStatus.out_of_scope
    write_audit_event(
        db,
        document_id=document_id,
        actor_role=role.id,
        event_type="workflow.transition",
        from_state=old_status,
        to_state="out_of_scope",
    )
    db.commit()
    return {"document": document, "message": "Document marked as out of scope"}


@router.post("/{document_id}/close")
async def close_document(
    document_id: str,
    role: CurrentRole = Depends(require_action("documents.close")),
    db: Session = Depends(get_db),
):
    """Close document — supervisor only."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    try:
        # Transition to approved if not already
        if document.status != DocumentStatus.approved:
            validate_transition(document.status, DocumentStatus.approved)
            old_status = document.status.value
            document.status = DocumentStatus.approved
            write_audit_event(
                db,
                document_id=document_id,
                actor_role=role.id,
                event_type="workflow.transition",
                from_state=old_status,
                to_state="approved",
            )

        validate_transition(document.status, DocumentStatus.closed)
        old_status = document.status.value
        document.status = DocumentStatus.closed
        write_audit_event(
            db,
            document_id=document_id,
            actor_role=role.id,
            event_type="workflow.transition",
            from_state=old_status,
            to_state="closed",
        )
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e), "details": {}}},
        )

    db.commit()
    return {"document": document, "message": "Document closed"}
