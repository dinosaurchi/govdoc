from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api import deps
from app.models.system import Role, Department, PromptVersion
from app.schemas.system import RoleOut, DepartmentOut, PromptVersionOut

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(db: Session = Depends(deps.get_db)):
    """List all seeded roles. No auth required."""
    return db.query(Role).all()


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(db: Session = Depends(deps.get_db)):
    """List all departments. No auth required."""
    return db.query(Department).all()


@router.get("/prompt-versions", response_model=list[PromptVersionOut])
async def list_prompt_versions(db: Session = Depends(deps.get_db)):
    """List all registered prompt versions. No auth required."""
    return db.query(PromptVersion).all()
