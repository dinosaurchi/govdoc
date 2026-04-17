from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import settings
from app.core.config_loader import load_prompt_versions_config
from app.db.session import SessionLocal
from app.services.demo import seed_all
from app.services.file_validation import FileValidationError
from app.services.prompt_registry import PromptRegistry
from app.services.workflow import InvalidTransitionError

# Resolve paths relative to the project root regardless of CWD
# main.py is at: api/app/main.py  → 2 parents up = api/ , 3 = project root
_API_ROOT = Path(__file__).resolve().parent.parent  # api/
_PROJECT_ROOT = _API_ROOT.parent  # govdoc/


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup — seed roles/departments and register prompt versions
    db = SessionLocal()
    try:
        seed_all(db)
        prompt_versions_path = _PROJECT_ROOT / "api/config/prompt_versions.yaml"
        prompts_dir = _PROJECT_ROOT / settings.PROMPT_CONFIG_PATH
        labels = load_prompt_versions_config(prompt_versions_path)
        registry = PromptRegistry(prompts_dir, db, labels)
        registry.register_all()
        _app.state.prompt_registry = registry
    finally:
        db.close()
    yield
    # Shutdown (nothing to do)


app = FastAPI(
    title="GovDoc SecureFlow API",
    description="Backend for public-sector document intake and triage",
    version="0.1.0",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(FileValidationError)
async def file_validation_error_handler(request: Request, exc: FileValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": {"code": exc.code, "message": exc.message, "details": {}}},
    )


@app.exception_handler(InvalidTransitionError)
async def invalid_transition_error_handler(request: Request, exc: InvalidTransitionError):
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "INVALID_TRANSITION", "message": str(exc), "details": {}}},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "PERSISTENCE_FAILED", "message": str(exc), "details": {}}},
    )


@app.get("/healthz")
def health_check():
    """Liveness: process is up (no DB check)."""
    return {"status": "ok"}


@app.get("/readyz")
def ready_check():
    """Readiness: database is reachable (docker-compose should use this)."""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database_unavailable: {exc}") from exc
    finally:
        db.close()
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
