import uuid
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DocumentStatus(str, Enum):
    received = "received"
    extracted = "extracted"
    analyzed = "analyzed"
    routed = "routed"
    under_review = "under_review"
    in_consultation = "in_consultation"
    approved = "approved"
    closed = "closed"
    out_of_scope = "out_of_scope"
    ingest_failed = "ingest_failed"
    analysis_failed = "analysis_failed"


class SecurityLevel(str, Enum):
    unclassified = "unclassified"
    confidential = "confidential"
    secret = "secret"
    top_secret = "top_secret"


class Urgency(str, Enum):
    normal = "normal"
    urgent = "urgent"
    critical = "critical"


class ExtractionMethod(str, Enum):
    pypdf = "pypdf"
    render_ocr = "render_ocr"
    qwen_ocr = "qwen-ocr"
    docx = "docx"
    plaintext = "plaintext"


class AnalysisStage(str, Enum):
    classify = "classify"
    summarize = "summarize"
    route = "route"
    escalate = "escalate"


class AnalysisSource(str, Enum):
    live = "live"
    cached = "cached"


class RoutingDecisionType(str, Enum):
    accepted = "accepted"
    rerouted = "rerouted"
    escalated = "escalated"
    out_of_scope = "out_of_scope"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    doc_number = Column(String(100), nullable=True)
    issuing_agency = Column(String(255), nullable=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(SAEnum(DocumentStatus), nullable=False, default=DocumentStatus.received)
    security_level = Column(SAEnum(SecurityLevel), nullable=False, default=SecurityLevel.unclassified)
    urgency = Column(SAEnum(Urgency), nullable=False, default=Urgency.normal)
    assigned_department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    assigned_reviewer_role = Column(String(50), nullable=True)
    current_prompt_version = Column(String(12), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # relationships
    files = relationship("DocumentFile", back_populates="document", lazy="selectin")
    artifacts = relationship("ExtractedArtifact", back_populates="document", lazy="selectin")
    analyses = relationship("AIAnalysis", back_populates="document", lazy="selectin")
    routing_decisions = relationship("RoutingDecision", back_populates="document", lazy="selectin")
    consultation_notes = relationship("ConsultationNote", back_populates="document", lazy="selectin")
    audit_events = relationship("AuditEvent", back_populates="document", lazy="selectin")


class DocumentFile(Base):
    __tablename__ = "document_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    storage_key = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    is_primary = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="files")


class ExtractedArtifact(Base):
    __tablename__ = "extracted_artifacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    extraction_method = Column(SAEnum(ExtractionMethod), nullable=False)
    text = Column(Text, nullable=False)
    page_count = Column(Integer, default=1)
    warnings = Column(JSON, default=list)  # list[str]
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="artifacts")


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    stage = Column(SAEnum(AnalysisStage), nullable=False)
    model_name = Column(String(100), nullable=False)
    prompt_version = Column(String(12), nullable=False)
    source = Column(SAEnum(AnalysisSource), nullable=False, default=AnalysisSource.live)
    payload_json = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="analyses")


class RoutingDecision(Base):
    __tablename__ = "routing_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    suggested_department_id = Column(String(36), nullable=True)
    final_department_id = Column(String(36), nullable=True)
    decided_by_role = Column(String(50), nullable=True)
    decision = Column(SAEnum(RoutingDecisionType), nullable=False)
    rationale = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="routing_decisions")


class ConsultationNote(Base):
    __tablename__ = "consultation_notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    author_role = Column(String(50), nullable=False)
    target_role = Column(String(50), nullable=True)
    body = Column(Text, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="consultation_notes")
