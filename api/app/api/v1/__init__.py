from fastapi import APIRouter
from app.api.v1.endpoints import documents, review, consultation, dashboard, demo, meta, retrieval

api_router = APIRouter()

# Meta endpoints (no auth required)
api_router.include_router(meta.router)

# Document endpoints (auth required)
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])

# Workflow action endpoints (auth required) — review router already has prefix="/documents"
api_router.include_router(review.router)

# Legacy consultation endpoints — kept for backward compat
api_router.include_router(consultation.router, prefix="/consultation", tags=["consultation"])

# Dashboard
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])

# Demo endpoints
api_router.include_router(demo.router)

# Retrieval endpoints
api_router.include_router(retrieval.router)
