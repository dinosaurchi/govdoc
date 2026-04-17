"""Comprehensive unit tests for the workflow state machine."""

import pytest

from app.models.document import DocumentStatus
from app.services.workflow import (
    InvalidTransitionError,
    VALID_TRANSITIONS,
    validate_transition,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# All valid (current, target) pairs flattened from VALID_TRANSITIONS
_VALID_PAIRS: list[tuple[DocumentStatus, DocumentStatus]] = []
for _current, _targets in VALID_TRANSITIONS.items():
    for _target in _targets:
        _VALID_PAIRS.append((_current, _target))

# Terminal / error states
_TERMINAL_STATES = {
    DocumentStatus.closed,
    DocumentStatus.out_of_scope,
    DocumentStatus.ingest_failed,
    DocumentStatus.analysis_failed,
}

# Non-terminal states
_NON_TERMINAL = set(DocumentStatus) - _TERMINAL_STATES


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestValidTransitions:
    """Test that every transition listed in VALID_TRANSITIONS passes validation."""

    @pytest.mark.parametrize("current,target", _VALID_PAIRS, ids=lambda v: v.value)
    def test_valid_transition_passes(self, current, target):
        validate_transition(current, target)  # should not raise


@pytest.mark.unit
class TestInvalidTransitions:
    """Test that transitions NOT listed in VALID_TRANSITIONS raise InvalidTransitionError."""

    @pytest.mark.parametrize("current", list(DocumentStatus))
    def test_unlisted_transition_raises(self, current):
        """Every target NOT in the allowed set should raise."""
        allowed = VALID_TRANSITIONS.get(current, set())
        for target in DocumentStatus:
            if target == current or target in allowed:
                continue
            with pytest.raises(InvalidTransitionError) as exc_info:
                validate_transition(current, target)
            assert exc_info.value.current == current.value
            assert exc_info.value.target == target.value


@pytest.mark.unit
class TestSameStateTransition:
    """Same-state (idempotent) transitions should always be allowed."""

    @pytest.mark.parametrize("status", list(DocumentStatus))
    def test_same_state_is_ok(self, status):
        validate_transition(status, status)  # should not raise


@pytest.mark.unit
class TestTerminalStates:
    """Terminal and error states should have no outgoing transitions."""

    @pytest.mark.parametrize("status", list(_TERMINAL_STATES))
    def test_no_outgoing_transitions(self, status):
        assert len(VALID_TRANSITIONS.get(status, set())) == 0

    @pytest.mark.parametrize("status", list(_TERMINAL_STATES))
    def test_any_transition_from_terminal_raises(self, status):
        for target in DocumentStatus:
            if target == status:
                continue
            with pytest.raises(InvalidTransitionError):
                validate_transition(status, target)


@pytest.mark.unit
class TestInvalidTransitionErrorAttributes:
    def test_error_message_format(self):
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition(DocumentStatus.closed, DocumentStatus.received)
        err = exc_info.value
        assert err.current == "closed"
        assert err.target == "received"
        assert "closed" in str(err)
        assert "received" in str(err)
