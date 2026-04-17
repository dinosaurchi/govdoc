import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.document import AnalysisStage


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(50), primary_key=True)  # e.g. "intake_clerk"
    label = Column(String(100), nullable=False)
    allowed_actions = Column(JSON, default=list)  # list[str]
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    actor_role = Column(String(50), nullable=True)
    event_type = Column(String(100), nullable=False)
    from_state = Column(String(50), nullable=True)
    to_state = Column(String(50), nullable=True)
    metadata_json = Column(JSON, default=dict)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="audit_events")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(String(12), primary_key=True)  # SHA-256[:12]
    stage = Column(SAEnum(AnalysisStage), primary_key=True)  # composite PK
    file_path = Column(String(500), nullable=False)
    label = Column(String(255), nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())


class DemoScenario(Base):
    __tablename__ = "demo_scenarios"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=True)
    category = Column(String(50), nullable=True)  # hero, ambiguity, scan, out_of_scope
    created_at = Column(DateTime(timezone=True), server_default=func.now())
