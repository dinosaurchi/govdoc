from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any, Dict, List


class RoleOut(BaseModel):
    id: str
    label: str
    allowed_actions: List[str] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditEventOut(BaseModel):
    id: str
    document_id: Optional[str] = None
    actor_role: Optional[str] = None
    event_type: str
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardMetrics(BaseModel):
    total_received: int
    pending_review: int
    under_consultation: int
    closed_today: int
