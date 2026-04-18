from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api import deps
from app.api.deps import require_action, CurrentRole
from app.models.system import DemoScenario, Role, Department
from app.schemas.system import DemoScenarioOut
from app.services.demo import seed_all
from app.core.config import settings

router = APIRouter(prefix="/demo", tags=["demo"])

# api/app/api/v1/endpoints/demo.py → parents[5] = repo root (govdoc/)
_PROJECT_ROOT = Path(__file__).resolve().parents[5]
_DEMO_SAMPLE_FILES = frozenset(
    {
        "sample-cong-van-dong-nai.pdf",
        "sample-bao-cao-dong-nai.pdf",
    }
)


def _demo_sample_pdf_dir() -> Path:
    """Prefer Docker-bundled PDFs; fall back to web/public/demo in local dev."""
    docker_dir = Path("/app/demo-sample-pdfs")
    if docker_dir.is_dir() and any(docker_dir.glob("*.pdf")):
        return docker_dir
    return _PROJECT_ROOT / "web" / "public" / "demo"


@router.get("/sample-files/{filename}")
async def download_demo_sample_file(filename: str) -> FileResponse:
    """Serve bundled demo PDFs via the API so downloads work through /api/ (nginx proxy) with correct MIME type."""
    if filename not in _DEMO_SAMPLE_FILES:
        raise HTTPException(status_code=404, detail="Unknown sample file")
    path = _demo_sample_pdf_dir() / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Sample file not available on server")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        content_disposition_type="attachment",
    )


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
