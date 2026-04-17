from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Any, Dict

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleOut(RoleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DepartmentBase(BaseModel):
    name: str
    code: str

class DepartmentOut(DepartmentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class AuditEventOut(BaseModel):
    id: int
    document_id: Optional[int]
    actor_role_id: int
    action: str
    details: Optional[Dict[str, Any]]
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class DashboardMetrics(BaseModel):
    total_received: int
    pending_review: int
    under_consultation: int
    closed_today: int
