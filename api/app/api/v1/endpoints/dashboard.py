from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api import deps
from app.schemas.system import DashboardMetrics
from app.models.document import Document, DocumentStatus

router = APIRouter()


@router.get("/stats", response_model=DashboardMetrics)
async def get_dashboard_stats(db: Session = Depends(deps.get_db), role: str = Depends(deps.get_current_role)):
    # Real database counts
    counts = db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()
    stats_map = {state: count for state, count in counts}

    return {
        "total_received": db.query(Document).count(),
        "pending_review": stats_map.get(DocumentStatus.received, 0)
        + stats_map.get(DocumentStatus.extracted, 0)
        + stats_map.get(DocumentStatus.analyzed, 0)
        + stats_map.get(DocumentStatus.routed, 0),
        "under_consultation": stats_map.get(DocumentStatus.in_consultation, 0),
        "closed_today": stats_map.get(DocumentStatus.closed, 0) + stats_map.get(DocumentStatus.approved, 0),
    }
