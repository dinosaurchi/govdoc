from typing import Generator, Optional
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

from app.services.ai.interface import AIProviderInterface
from app.services.ai.mock_provider import MockAIProvider
from app.services.extraction.interface import ExtractionProviderInterface
from app.services.extraction.mock_provider import MockExtractionProvider
from app.services.retrieval.interface import RetrievalProviderInterface
from app.services.retrieval.mock_provider import MockRetrievalProvider

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_ai_provider() -> AIProviderInterface:
    return MockAIProvider()

def get_extraction_provider() -> ExtractionProviderInterface:
    return MockExtractionProvider()

def get_retrieval_provider() -> RetrievalProviderInterface:
    return MockRetrievalProvider()

def get_current_role(x_role: Optional[str] = Header(None)) -> str:
    # In Pass 1.5, we simulate role-based access via a header
    # If no header is provided, we default to a safe baseline or error
    if not x_role:
        # For development ease, maybe default to Clerk, but prompt implies policy scaffold
        return "Intake Clerk"
    
    valid_roles = ["Intake Clerk", "Department Reviewer", "Consultant", "Supervisor"]
    if x_role not in valid_roles:
        raise HTTPException(status_code=403, detail="Invalid role context")
    return x_role

def require_role(allowed_roles: list[str]):
    def role_checker(role: str = Depends(get_current_role)):
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Role {role} not authorized for this action")
        return role
    return role_checker
