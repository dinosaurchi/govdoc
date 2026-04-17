"""Deterministic audit logging — not mock AI; every mutation should call this."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.system import AuditEvent


def write_audit_event(
    db: Session,
    *,
    document_id: Optional[str],
    actor_role: str,
    event_type: str,
    from_state: Optional[str] = None,
    to_state: Optional[str] = None,
    metadata_json: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    row = AuditEvent(
        document_id=document_id,
        actor_role=actor_role,
        event_type=event_type,
        from_state=from_state,
        to_state=to_state,
        metadata_json=metadata_json or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
