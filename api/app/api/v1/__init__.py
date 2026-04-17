from fastapi import APIRouter
from app.api.v1.endpoints import documents, review, consultation, dashboard, demo

api_router = APIRouter()
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(consultation.router, prefix="/consultation", tags=["consultation"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
