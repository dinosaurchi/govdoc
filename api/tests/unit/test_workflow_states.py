"""Lightweight unit checks for domain enums (structure for later workflow tests)."""

import pytest

from app.models.document import DocumentStatus


@pytest.mark.unit
def test_document_status_count_matches_spec():
    # Spec: 11 statuses in DocumentStatus enum
    assert len(DocumentStatus.__members__) == 11


@pytest.mark.unit
def test_document_status_expected_values():
    expected = {
        "received",
        "extracted",
        "analyzed",
        "routed",
        "under_review",
        "in_consultation",
        "approved",
        "closed",
        "out_of_scope",
        "ingest_failed",
        "analysis_failed",
    }
    assert set(DocumentStatus.__members__.keys()) == expected
