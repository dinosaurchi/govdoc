from pydantic import BaseModel
from datetime import datetime


class RoleOut(BaseModel):
    id: str
    label: str
    allowed_actions: list[str] = []

    class Config:
        from_attributes = True


class DepartmentOut(BaseModel):
    id: str
    name: str
    description: str | None = None

    class Config:
        from_attributes = True


class PromptVersionOut(BaseModel):
    id: str
    stage: str
    file_path: str
    label: str | None = None
    registered_at: datetime

    class Config:
        from_attributes = True


class DemoScenarioOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    document_id: str | None = None
    category: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class DashboardMetrics(BaseModel):
    total_received: int
    pending_review: int
    under_consultation: int
    closed_today: int
