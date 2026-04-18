from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_db, require_action, CurrentRole
from app.models.document import Document, DocumentStatus, RoutingDecision, ConsultationNote
from app.models.system import Department
from app.services.workflow import validate_transition, InvalidTransitionError
from app.services.audit_service import write_audit_event
from app.schemas.document import (
    ConsultationActionResponse,
    ConsultationNoteOut,
    ConsultationRequest,
    RerouteRequest,
    RoutingActionResponse,
    RoutingDecisionOut,
    WorkflowActionResponse,
)
import uuid

router = APIRouter(prefix="/documents", tags=["workflow"])


def _count_unresolved_consultation_notes(db: Session, document_id: str) -> int:
    return (
        db.query(ConsultationNote)
        .filter(
            ConsultationNote.document_id == document_id,
            ConsultationNote.resolved_at.is_(None),
        )
        .count()
    )


@router.post("/{document_id}/approve-routing", response_model=WorkflowActionResponse)
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

    # Look up the AI-produced routing decision (created during analysis with
    # decision="accepted" but final_department_id=None pending human review).
    # Accepting the AI suggestion means copying its suggested_department_id
    # onto both the routing decision and the document itself.
    ai_routing = (
        db.query(RoutingDecision)
        .filter(RoutingDecision.document_id == document_id)
        .order_by(RoutingDecision.created_at.desc())
        .first()
    )
    if ai_routing is None or not ai_routing.suggested_department_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "NO_AI_ROUTING",
                    "message": (
                        "Document has no AI routing suggestion to approve. "
                        "Re-run analysis or use reroute-document instead."
                    ),
                    "details": {},
                }
            },
        )

    ai_routing.final_department_id = ai_routing.suggested_department_id
    ai_routing.decided_by_role = role.id

    document.status = DocumentStatus.routed
    document.assigned_reviewer_role = role.id
    document.assigned_department_id = ai_routing.suggested_department_id

    write_audit_event(
        db,
        document_id=document_id,
        actor_role=role.id,
        event_type="workflow.transition",
        from_state=old_status,
        to_state="routed",
        metadata_json={"department_id": ai_routing.suggested_department_id},
    )
    db.commit()
    return {"document": document, "message": "Routing approved"}


@router.post("/{document_id}/reroute", response_model=RoutingActionResponse)
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
    try:
        validate_transition(document.status, DocumentStatus.routed)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e), "details": {}}},
        )

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


@router.post("/{document_id}/request-consultation", response_model=ConsultationActionResponse)
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


@router.post("/{document_id}/resolve-consultation/{note_id}", response_model=ConsultationActionResponse)
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

    document = db.query(Document).filter(Document.id == document_id).first()
    if document:
        # Guard against resolving notes on documents in terminal states.
        # The only statuses where resolving a note makes sense are
        # `in_consultation` (the normal case) and `under_review` (a prior
        # run of this endpoint already flipped the doc back but an earlier
        # bug left sibling notes open — resolving them is still valid).
        try:
            validate_transition(document.status, DocumentStatus.under_review)
        except InvalidTransitionError as e:
            raise HTTPException(
                status_code=400,
                detail={"error": {"code": "INVALID_TRANSITION", "message": str(e), "details": {}}},
            )

    note.resolved_at = func.now()
    # `flush` so the just-resolved note's `resolved_at` is visible to the
    # subsequent "are there still open notes?" query below.
    db.flush()

    if document:
        unresolved_remaining = (
            db.query(ConsultationNote)
            .filter(
                ConsultationNote.document_id == document_id,
                ConsultationNote.resolved_at.is_(None),
            )
            .count()
        )

        # Only flip back to `under_review` once every open note has been
        # resolved. In a parallel-consultation scenario (e.g. reviewer
        # asked both Legal and Consultant) resolving a single note should
        # leave the document on `in_consultation` until the last one is
        # handled. If the document is already on `under_review` (data
        # drift from an older buggy run), just resolve the note and leave
        # the status alone.
        if (
            unresolved_remaining == 0
            and document.status == DocumentStatus.in_consultation
        ):
            old_status = document.status.value
            document.status = DocumentStatus.under_review
            write_audit_event(
                db,
                document_id=document_id,
                actor_role=role.id,
                event_type="workflow.transition",
                from_state=old_status,
                to_state="under_review",
                metadata_json={"resolved_note_id": note_id},
            )
    db.commit()
    return {"document": document, "consultation_note": note}


@router.post("/{document_id}/escalate", response_model=WorkflowActionResponse)
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


@router.post("/{document_id}/mark-out-of-scope", response_model=WorkflowActionResponse)
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

    try:
        validate_transition(document.status, DocumentStatus.out_of_scope)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e), "details": {}}},
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


@router.post("/{document_id}/approve", response_model=WorkflowActionResponse)
async def approve_document(
    document_id: str,
    role: CurrentRole = Depends(require_action("documents.approve")),
    db: Session = Depends(get_db),
):
    """Approve the document — transitions to `approved` (archive/close is separate).

    Allowed from `under_review` or `in_consultation`. Blocked while consultation
    notes are still open so approval cannot skip parallel review work.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    open_notes = _count_unresolved_consultation_notes(db, document_id)
    if open_notes > 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "OPEN_CONSULTATION_NOTES",
                    "message": "Resolve all consultation notes before approving.",
                    "details": {"open_notes": open_notes},
                }
            },
        )

    try:
        validate_transition(document.status, DocumentStatus.approved)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e), "details": {}}},
        )

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
    db.commit()
    return {"document": document, "message": "Document approved"}


@router.post("/{document_id}/close", response_model=WorkflowActionResponse)
async def close_document(
    document_id: str,
    role: CurrentRole = Depends(require_action("documents.close")),
    db: Session = Depends(get_db),
):
    """Close document — supervisor only, from `approved` to `closed`."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "NOT_FOUND", "message": "Document not found", "details": {}}},
        )

    try:
        validate_transition(document.status, DocumentStatus.closed)
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_TRANSITION", "message": str(e), "details": {}}},
        )

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
    db.commit()
    return {"document": document, "message": "Document closed"}
