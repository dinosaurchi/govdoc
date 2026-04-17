from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.system import Role


def get_role_id_by_name(db: Session, name: str) -> int:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        raise HTTPException(
            status_code=500,
            detail="Role registry not seeded; call POST /api/v1/demo/seed first",
        )
    return role.id
