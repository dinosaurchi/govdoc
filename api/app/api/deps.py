"""Dependency injection for FastAPI endpoints."""

from typing import Generator, Optional

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

from app.services.ai.interface import AIProvider
from app.services.ai.mock_provider import MockAIProvider
from app.services.extraction.interface import ExtractionProviderInterface
from app.services.extraction.mock_provider import MockExtractionProvider
from app.services.retrieval.interface import RetrievalProviderInterface
from app.services.retrieval.mock_provider import MockRetrievalProvider

from app.core.config_loader import load_roles_config
from app.core.config import settings
from pathlib import Path

# Resolve paths relative to the project root regardless of CWD
# deps.py is at: api/app/api/deps.py  → 3 parents up = api/ , 4 = project root
_API_ROOT = Path(__file__).resolve().parent.parent.parent  # api/
_PROJECT_ROOT = _API_ROOT.parent  # govdoc/


# ---------------------------------------------------------------------------
# Database / Provider dependencies (unchanged)
# ---------------------------------------------------------------------------


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_ai_provider() -> AIProvider:
    return MockAIProvider()


def get_extraction_provider() -> ExtractionProviderInterface:
    return MockExtractionProvider()


def get_retrieval_provider() -> RetrievalProviderInterface:
    return MockRetrievalProvider()


# ---------------------------------------------------------------------------
# Role-based permission enforcement
# ---------------------------------------------------------------------------


class CurrentRole:
    def __init__(self, role_id: str, label: str, allowed_actions: list[str]):
        self.id = role_id
        self.label = label
        self.allowed_actions = allowed_actions

    def has_action(self, action: str) -> bool:
        return action in self.allowed_actions


# Cache loaded roles
_roles_cache: dict[str, CurrentRole] | None = None


def _load_roles() -> dict[str, CurrentRole]:
    global _roles_cache
    if _roles_cache is None:
        config_path = _PROJECT_ROOT / settings.ROLES_CONFIG_PATH
        config = load_roles_config(config_path)
        _roles_cache = {}
        for role_id, role_data in config["roles"].items():
            _roles_cache[role_id] = CurrentRole(
                role_id=role_id,
                label=role_data["label"],
                allowed_actions=role_data.get("allowed_actions", []),
            )
    return _roles_cache


def _reset_roles_cache() -> None:
    """Clear the roles cache (for testing)."""
    global _roles_cache
    _roles_cache = None


def get_current_role(
    x_govdoc_role: Optional[str] = Header(default=None, alias="X-GovDoc-Role"),
) -> CurrentRole:
    if x_govdoc_role is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "MISSING_ROLE_HEADER",
                    "message": "X-GovDoc-Role header is required",
                    "details": {},
                }
            },
        )
    roles = _load_roles()
    if x_govdoc_role not in roles:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": "UNKNOWN_ROLE",
                    "message": f"Unknown role: {x_govdoc_role}",
                    "details": {},
                }
            },
        )
    return roles[x_govdoc_role]


def require_action(action: str):
    """Dependency that checks if current role has the required action."""

    async def checker(role: CurrentRole = Depends(get_current_role)):
        if not role.has_action(action):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "FORBIDDEN_ACTION",
                        "message": f"Role '{role.id}' does not have action '{action}'",
                        "details": {},
                    }
                },
            )
        return role

    return checker
