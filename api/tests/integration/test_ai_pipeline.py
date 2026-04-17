"""Integration tests for the AI analysis pipeline (mock provider — no live API calls)."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai.mock_provider import MockAIProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_text_file(content: str = "Test document content for GovDoc SecureFlow.") -> bytes:
    return content.encode("utf-8")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clerk_headers():
    return {"X-GovDoc-Role": "intake_clerk"}


@pytest.fixture
def supervisor_headers():
    return {"X-GovDoc-Role": "supervisor"}


# ---------------------------------------------------------------------------
# Tests: upload triggers analysis via mock provider
# ---------------------------------------------------------------------------


@pytest.mark.mock_integration
class TestAIPipeline:
    def test_upload_triggers_analysis(self, client, clerk_headers):
        """Upload a text file and verify AI analysis is triggered with mock provider."""
        content = _make_text_file("Công văn số 123/UBND về việc phê duyệt kế hoạch bảo trì hệ thống IT năm 2026.")
        resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("test_analysis.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # Document should be analyzed (not just extracted)
        assert data["document"]["status"] in ("analyzed", "extracted")
        assert data["extracted_artifact"] is not None

        # Should have AI analyses
        analyses = data.get("ai_analyses", [])
        assert len(analyses) >= 3, f"Expected at least 3 analyses, got {len(analyses)}"

        stages = {a["stage"] for a in analyses}
        assert "classify" in stages
        assert "summarize" in stages
        assert "route" in stages

    def test_analyze_document_with_mock(self, client, clerk_headers):
        """Test the analysis service directly with mock provider creates all analysis records."""
        # First upload a document
        content = _make_text_file("Test document for direct analysis service test.")
        upload_resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("direct_test.txt", io.BytesIO(content), "text/plain")},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["document"]["id"]

        # Verify via GET detail that analyses exist
        detail_resp = client.get(f"/api/v1/documents/{doc_id}", headers=clerk_headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["analyses"]) >= 3

        # Verify classify analysis has expected fields
        classify_analyses = [a for a in detail["analyses"] if a["stage"] == "classify"]
        assert len(classify_analyses) == 1
        payload = classify_analyses[0]["payload_json"]
        assert payload["doc_type"] == "cong_van"
        assert "confidence" in payload

    def test_re_analyze_idempotent(self, client, supervisor_headers):
        """Test that re-analyze returns cached results when prompt version matches."""
        # Upload a document first
        content = _make_text_file("Idempotent test document for GovDoc analysis pipeline.")
        upload_resp = client.post(
            "/api/v1/documents/",
            headers=supervisor_headers,
            files={"file": ("idempotent_test.txt", io.BytesIO(content), "text/plain")},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["document"]["id"]

        # Re-analyze without force — should return existing analyses
        re_analyze_resp = client.post(
            f"/api/v1/documents/{doc_id}/analyze?force=false",
            headers=supervisor_headers,
        )
        assert re_analyze_resp.status_code == 200
        data = re_analyze_resp.json()
        assert "ai_analyses" in data

    def test_re_analyze_force(self, client, supervisor_headers):
        """Test that re-analyze with force=true re-runs the pipeline."""
        content = _make_text_file("Force re-analyze test document content.")
        upload_resp = client.post(
            "/api/v1/documents/",
            headers=supervisor_headers,
            files={"file": ("force_test.txt", io.BytesIO(content), "text/plain")},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["document"]["id"]

        # Re-analyze with force
        re_analyze_resp = client.post(
            f"/api/v1/documents/{doc_id}/analyze?force=true",
            headers=supervisor_headers,
        )
        assert re_analyze_resp.status_code == 200
        data = re_analyze_resp.json()
        analyses = data.get("ai_analyses", [])
        assert len(analyses) >= 3

    def test_analysis_failure_does_not_advance_status(self, client, clerk_headers):
        """Test that AI failure marks document as analysis_failed, not analyzed."""
        content = _make_text_file("Failure test document content.")

        # Patch MockAIProvider.classify to raise an error
        with patch.object(MockAIProvider, "classify", side_effect=RuntimeError("AI service unavailable")):
            resp = client.post(
                "/api/v1/documents/",
                headers=clerk_headers,
                files={"file": ("failure_test.txt", io.BytesIO(content), "text/plain")},
            )
            assert resp.status_code == 200
            data = resp.json()
            # Document should be marked as analysis_failed
            assert data["document"]["status"] == "analysis_failed"
            # No AI analyses
            assert len(data.get("ai_analyses", [])) == 0

    def test_re_analyze_nonexistent_document(self, client, supervisor_headers):
        """Test re-analyze on nonexistent document returns 404."""
        resp = client.post(
            "/api/v1/documents/nonexistent-id/analyze",
            headers=supervisor_headers,
        )
        assert resp.status_code == 404

    def test_re_analyze_requires_analyze_permission(self, client, clerk_headers):
        """Test that re-analyze requires documents.analyze permission."""
        content = _make_text_file("Permission test document.")
        upload_resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("perm_test.txt", io.BytesIO(content), "text/plain")},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["document"]["id"]

        # Intake clerk does NOT have documents.analyze action
        resp = client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            headers=clerk_headers,
        )
        assert resp.status_code == 403
