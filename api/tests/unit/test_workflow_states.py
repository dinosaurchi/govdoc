"""Lightweight unit checks for domain enums (structure for later workflow tests)."""

import pytest

from app.models.document import WorkflowState


@pytest.mark.unit
def test_workflow_state_count_matches_source_of_truth():
    # Source: docs/govdoc_source_of_truth_plan_v1_1.md — 10 states
    assert len(WorkflowState.__members__) == 10
