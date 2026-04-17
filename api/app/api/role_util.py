from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.system import Role


def get_role_id_by_name(db: Session, label: str) -> str:
    """Look up a Role by its label (e.g. 'Intake Clerk') and return its string PK id."""
    role = db.query(Role).filter(Role.label == label).first()
    if not role:
        raise HTTPException(
            status_code=500,
            detail="Role registry not seeded; call POST /api/v1/demo/seed first",
        )
    return role.id
