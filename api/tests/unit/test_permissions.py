"""Unit tests for role-based permission enforcement."""

import pytest
from unittest.mock import patch

from fastapi import HTTPException

from app.api.deps import (
    CurrentRole,
    _load_roles,
    _reset_roles_cache,
    get_current_role,
    require_action,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_ROLES_CONFIG = {
    "roles": {
        "intake_clerk": {
            "label": "Intake Clerk",
            "allowed_actions": ["documents.create", "documents.read", "documents.list"],
        },
        "reviewer": {
            "label": "Reviewer",
            "allowed_actions": [
                "documents.read",
                "documents.list",
                "documents.review",
            ],
        },
        "supervisor": {
            "label": "Supervisor",
            "allowed_actions": [
                "documents.read",
                "documents.close",
                "documents.escalate",
                "demo.reset",
            ],
        },
    }
}


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the global roles cache before each test."""
    _reset_roles_cache()
    yield
    _reset_roles_cache()


# ---------------------------------------------------------------------------
# CurrentRole tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCurrentRole:
    def test_has_action_true(self):
        role = CurrentRole("clerk", "Clerk", ["documents.create", "documents.read"])
        assert role.has_action("documents.create") is True

    def test_has_action_false(self):
        role = CurrentRole("clerk", "Clerk", ["documents.create"])
        assert role.has_action("documents.close") is False

    def test_empty_actions(self):
        role = CurrentRole("none", "No Actions", [])
        assert role.has_action("any") is False


# ---------------------------------------------------------------------------
# _load_roles tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoadRoles:
    @patch("app.api.deps.load_roles_config")
    def test_loads_roles_from_config(self, mock_load):
        mock_load.return_value = SAMPLE_ROLES_CONFIG
        roles = _load_roles()
        assert "intake_clerk" in roles
        assert "reviewer" in roles
        assert "supervisor" in roles
        assert roles["intake_clerk"].label == "Intake Clerk"
        assert roles["intake_clerk"].id == "intake_clerk"

    @patch("app.api.deps.load_roles_config")
    def test_caches_roles(self, mock_load):
        mock_load.return_value = SAMPLE_ROLES_CONFIG
        _load_roles()
        _load_roles()
        # Should only call load_roles_config once due to caching
        mock_load.assert_called_once()


# ---------------------------------------------------------------------------
# get_current_role tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCurrentRole:
    @patch("app.api.deps.load_roles_config")
    def test_valid_role_returns_current_role(self, mock_load):
        mock_load.return_value = SAMPLE_ROLES_CONFIG
        role = get_current_role(x_govdoc_role="intake_clerk")
        assert isinstance(role, CurrentRole)
        assert role.id == "intake_clerk"
        assert role.label == "Intake Clerk"

    def test_missing_header_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            get_current_role(x_govdoc_role=None)
        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        # Check structured error format
        assert "error" in detail
        assert detail["error"]["code"] == "MISSING_ROLE_HEADER"

    @patch("app.api.deps.load_roles_config")
    def test_unknown_role_raises_403(self, mock_load):
        mock_load.return_value = SAMPLE_ROLES_CONFIG
        with pytest.raises(HTTPException) as exc_info:
            get_current_role(x_govdoc_role="unknown_role")
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert "error" in detail
        assert detail["error"]["code"] == "UNKNOWN_ROLE"


# ---------------------------------------------------------------------------
# require_action tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequireAction:
    @pytest.mark.asyncio
    @patch("app.api.deps.load_roles_config")
    async def test_allowed_action_passes(self, mock_load):
        mock_load.return_value = SAMPLE_ROLES_CONFIG
        checker = require_action("documents.create")
        role = CurrentRole("intake_clerk", "Intake Clerk", ["documents.create"])
        result = await checker(role=role)
        assert result.id == "intake_clerk"

    @pytest.mark.asyncio
    async def test_forbidden_action_raises_403(self):
        checker = require_action("documents.close")
        role = CurrentRole("intake_clerk", "Intake Clerk", ["documents.create"])
        with pytest.raises(HTTPException) as exc_info:
            await checker(role=role)
        assert exc_info.value.status_code == 403
        detail = exc_info.value.detail
        assert "error" in detail
        assert detail["error"]["code"] == "FORBIDDEN_ACTION"
        assert "documents.close" in detail["error"]["message"]

    @pytest.mark.asyncio
    async def test_supervisor_has_escalate(self):
        checker = require_action("documents.escalate")
        role = CurrentRole("supervisor", "Supervisor", ["documents.escalate"])
        result = await checker(role=role)
        assert result.id == "supervisor"

    @pytest.mark.asyncio
    async def test_clerk_no_escalate(self):
        checker = require_action("documents.escalate")
        role = CurrentRole("intake_clerk", "Intake Clerk", ["documents.create"])
        with pytest.raises(HTTPException) as exc_info:
            await checker(role=role)
        assert exc_info.value.status_code == 403
