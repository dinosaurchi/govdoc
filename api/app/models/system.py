from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base
import datetime

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Intake Clerk, etc.
    description = Column(String, nullable=True)

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    code = Column(String, unique=True) # e.g. HR, IT, FIN

class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    actor_role_id = Column(Integer, ForeignKey("roles.id"))
    action = Column(String) # CREATE, ROUTE, CONSULT, etc.
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    document = relationship("Document", back_populates="audit_logs")

class DemoScenario(Base):
    __tablename__ = "demo_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    initial_data = Column(JSON) # Seed values
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True) # e.g. "intake-clarification"
    version = Column(Integer)
    template = Column(Text)
    active = Column(Integer, default=1) # 1 for True, 0 for False (SQLite friendly)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
