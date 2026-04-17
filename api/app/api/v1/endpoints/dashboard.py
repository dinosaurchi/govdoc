from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api import deps
from app.schemas.system import DashboardMetrics
from app.models.document import Document, WorkflowState

router = APIRouter()

@router.get("/stats", response_model=DashboardMetrics)
async def get_dashboard_stats(db: Session = Depends(deps.get_db), role: str = Depends(deps.get_current_role)):
    # Real database counts
    counts = db.query(Document.state, func.count(Document.id)).group_by(Document.state).all()
    stats_map = {state: count for state, count in counts}
    
    return {
        "total_received": db.query(Document).count(),
        "pending_review": stats_map.get(WorkflowState.registered, 0) + stats_map.get(WorkflowState.intake_received, 0),
        "under_consultation": stats_map.get(WorkflowState.consultation_requested, 0),
        "closed_today": stats_map.get(WorkflowState.closed, 0)
    }
