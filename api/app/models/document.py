from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import enum
import datetime

class WorkflowState(str, enum.Enum):
    intake_received = "intake_received"
    registered = "registered"
    routed_pending_human_review = "routed_pending_human_review"
    assigned_to_department = "assigned_to_department"
    under_review = "under_review"
    consultation_requested = "consultation_requested"
    consultation_completed = "consultation_completed"
    response_prepared = "response_prepared"
    closed = "closed"
    archived_demo_only = "archived_demo_only"

class DocumentType(str, enum.Enum):
    cong_van = "công văn"
    quyet_dinh = "quyết định"
    thong_bao = "thông báo"
    to_trinh = "tờ trình"
    bao_cao = "báo cáo"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    summary = Column(Text, nullable=True)
    doc_type = Column(Enum(DocumentType), default=DocumentType.cong_van)
    state = Column(Enum(WorkflowState), default=WorkflowState.intake_received)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    files = relationship("DocumentFile", back_populates="document")
    artifacts = relationship("ExtractedArtifact", back_populates="document")
    analysis = relationship("AIAnalysis", back_populates="document", uselist=False)
    decisions = relationship("RoutingDecision", back_populates="document")
    consultations = relationship("ConsultationNote", back_populates="document")
    audit_logs = relationship("AuditEvent", back_populates="document")

class DocumentFile(Base):
    __tablename__ = "document_files"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    file_path = Column(String)
    file_name = Column(String)
    mime_type = Column(String)
    
    document = relationship("Document", back_populates="files")

class ExtractedArtifact(Base):
    __tablename__ = "extracted_artifacts"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    key = Column(String)
    value = Column(Text)
    confidence = Column(Integer) # Percentage
    
    document = relationship("Document", back_populates="artifacts")

class AIAnalysis(Base):
    __tablename__ = "ai_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    suggested_type = Column(String)
    urgency_score = Column(Integer)
    summary = Column(Text)
    suggested_department = Column(String)
    raw_response = Column(Text)
    
    document = relationship("Document", back_populates="analysis")

class RoutingDecision(Base):
    __tablename__ = "routing_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    assigned_by_id = Column(Integer, ForeignKey("roles.id"))
    target_department_id = Column(Integer, ForeignKey("departments.id"))
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    document = relationship("Document", back_populates="decisions")

class ConsultationNote(Base):
    __tablename__ = "consultation_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    author_role_id = Column(Integer, ForeignKey("roles.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    document = relationship("Document", back_populates="consultations")
