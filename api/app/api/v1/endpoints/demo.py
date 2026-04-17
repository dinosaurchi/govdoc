from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.api.deps import require_action, CurrentRole
from app.models.system import DemoScenario, Role, Department
from app.schemas.system import DemoScenarioOut
from app.services.demo import seed_all
from app.core.config import settings

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/scenarios", response_model=list[DemoScenarioOut])
async def list_scenarios(db: Session = Depends(deps.get_db)):
    """List seeded demo scenarios."""
    return db.query(DemoScenario).all()


@router.post("/reset")
async def reset_demo(
    role: CurrentRole = Depends(require_action("demo.reset")),
    db: Session = Depends(deps.get_db),
):
    """Reset demo data (dev/demo env only)."""
    if settings.APP_ENV == "production":
        raise HTTPException(
            status_code=403,
            detail={"error": {"code": "FORBIDDEN_ACTION", "message": "Cannot reset demo in production", "details": {}}},
        )

    # Clear existing data
    db.query(DemoScenario).delete()
    db.query(Role).delete()
    db.query(Department).delete()

    # Re-seed
    seed_all(db)
    db.commit()
    return {"message": "Demo data reset successfully"}
