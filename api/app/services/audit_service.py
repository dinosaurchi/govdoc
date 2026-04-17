"""Deterministic audit logging — not mock AI; every mutation should call this."""

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.system import AuditEvent


def write_audit_event(
    db: Session,
    *,
    document_id: Optional[int],
    actor_role_id: int,
    action: str,
    details: Optional[dict[str, Any]] = None,
) -> AuditEvent:
    row = AuditEvent(
        document_id=document_id,
        actor_role_id=actor_role_id,
        action=action,
        details=details or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
