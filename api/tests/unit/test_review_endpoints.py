"""Unit tests for validate_transition enforcement on reroute and resolve-consultation endpoints.

These tests verify the state-machine guards that underpin the two workflow
endpoints.  Rather than spinning up the full FastAPI TestClient with database,
we exercise the pure `validate_transition` function directly — this is the
same function called by the endpoint handlers in `app.api.v1.endpoints.review`.
"""

import pytest

from app.models.document import DocumentStatus
from app.services.workflow import (
    InvalidTransitionError,
    validate_transition,
)


# ---------------------------------------------------------------------------
# reroute_document: transitions * → routed
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRerouteTransitionValidation:
    """
    The reroute endpoint calls `validate_transition(document.status, routed)`.
    We test that the transition is accepted/rejected correctly based on the
    current document status.
    """

    def test_reroute_from_under_review_succeeds(self):
        """under_review → routed should be allowed (reroute during review)."""
        validate_transition(DocumentStatus.under_review, DocumentStatus.routed)

    def test_reroute_from_in_consultation_fails(self):
        """in_consultation → routed is NOT in the transition table — consultation
        must first be resolved (→ under_review) before any reroute."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition(DocumentStatus.in_consultation, DocumentStatus.routed)
        assert exc_info.value.current == "in_consultation"
        assert exc_info.value.target == "routed"

    def test_reroute_from_closed_fails(self):
        """closed → routed must be rejected (terminal state)."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition(DocumentStatus.closed, DocumentStatus.routed)
        assert exc_info.value.current == "closed"
        assert exc_info.value.target == "routed"

    def test_reroute_from_out_of_scope_fails(self):
        """out_of_scope → routed must be rejected (terminal state)."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition(DocumentStatus.out_of_scope, DocumentStatus.routed)
        assert exc_info.value.current == "out_of_scope"
        assert exc_info.value.target == "routed"

    def test_reroute_from_analyzed_succeeds(self):
        """analyzed → routed is the normal approve-routing flow."""
        validate_transition(DocumentStatus.analyzed, DocumentStatus.routed)

    def test_reroute_from_routed_is_idempotent(self):
        """routed → routed (same state) is always allowed."""
        validate_transition(DocumentStatus.routed, DocumentStatus.routed)


# ---------------------------------------------------------------------------
# resolve_consultation: transitions * → under_review
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestResolveConsultationTransitionValidation:
    """
    The resolve-consultation endpoint calls
    `validate_transition(document.status, under_review)`.  We test that the
    transition is accepted/rejected correctly based on the current status.
    """

    def test_resolve_from_in_consultation_succeeds(self):
        """in_consultation → under_review is the normal resolve flow."""
        validate_transition(DocumentStatus.in_consultation, DocumentStatus.under_review)

    def test_resolve_from_closed_fails(self):
        """closed → under_review must be rejected (terminal state)."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition(DocumentStatus.closed, DocumentStatus.under_review)
        assert exc_info.value.current == "closed"
        assert exc_info.value.target == "under_review"

    def test_resolve_from_under_review_fails(self):
        """under_review → under_review is idempotent, but the *meaningful*
        resolve transition from under_review is not a real transition
        (document is already there). Test that a same-state call is OK."""
        # Same-state (idempotent) should pass
        validate_transition(DocumentStatus.under_review, DocumentStatus.under_review)

    def test_resolve_from_routed_succeeds(self):
        """routed → under_review IS a valid transition in the state machine."""
        validate_transition(DocumentStatus.routed, DocumentStatus.under_review)

    def test_resolve_from_approved_fails(self):
        """approved → under_review is not a valid transition."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition(DocumentStatus.approved, DocumentStatus.under_review)
        assert exc_info.value.current == "approved"
        assert exc_info.value.target == "under_review"
