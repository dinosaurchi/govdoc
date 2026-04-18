import pytest
from fastapi.testclient import TestClient


@pytest.mark.mock_integration
class TestRBACMatrix:
    """Test role × endpoint access matrix."""

    @pytest.fixture
    def client(self):
        from app.main import app

        with TestClient(app) as c:
            yield c

    @pytest.fixture
    def sample_doc_id(self, client):
        """Create a sample document and return its ID."""
        resp = client.post(
            "/api/v1/documents/",
            files={"file": ("test.txt", b"Test document content", "text/plain")},
            headers={"X-GovDoc-Role": "intake_clerk"},
        )
        assert resp.status_code == 200
        return resp.json()["document"]["id"]

    # Missing/unknown role tests
    def test_missing_role_header(self, client):
        resp = client.get("/api/v1/documents/")
        assert resp.status_code == 400
        assert resp.json()["detail"]["error"]["code"] == "MISSING_ROLE_HEADER"

    def test_unknown_role(self, client):
        resp = client.get("/api/v1/documents/", headers={"X-GovDoc-Role": "ghost"})
        assert resp.status_code == 403
        assert resp.json()["detail"]["error"]["code"] == "UNKNOWN_ROLE"

    # Endpoint × role tests
    @pytest.mark.parametrize("role", ["intake_clerk", "reviewer", "supervisor"])
    def test_documents_create_allowed(self, client, role):
        resp = client.post(
            "/api/v1/documents/",
            files={"file": ("test.txt", b"Test", "text/plain")},
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize("role", ["intake_clerk", "reviewer"])
    def test_documents_analyze_denied(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/analyze",
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 403

    def test_documents_analyze_allowed_supervisor(self, client, sample_doc_id):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/analyze",
            headers={"X-GovDoc-Role": "supervisor"},
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize("role", ["intake_clerk"])
    def test_approve_routing_denied(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/approve-routing",
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("role", ["reviewer", "supervisor"])
    def test_approve_routing_allowed(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/approve-routing",
            headers={"X-GovDoc-Role": role},
        )
        # May return 400 (invalid transition) or 200 — just not 403
        assert resp.status_code != 403

    @pytest.mark.parametrize("role", ["intake_clerk"])
    def test_reroute_denied(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/reroute",
            json={"department_id": "phong_hanh_chinh", "rationale": "test"},
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("role", ["intake_clerk"])
    def test_request_consultation_denied(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/request-consultation",
            json={"target_role": "reviewer", "body": "Need help"},
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("role", ["intake_clerk", "reviewer"])
    def test_escalate_denied(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/escalate",
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 403

    def test_escalate_allowed_supervisor(self, client, sample_doc_id):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/escalate",
            headers={"X-GovDoc-Role": "supervisor"},
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize("role", ["intake_clerk"])
    def test_close_denied(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/close",
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("role", ["intake_clerk", "consultant"])
    def test_approve_denied(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/approve",
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 403

    @pytest.mark.parametrize("role", ["reviewer", "supervisor"])
    def test_approve_allowed_not_403(self, client, sample_doc_id, role):
        resp = client.post(
            f"/api/v1/documents/{sample_doc_id}/approve",
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code != 403

    @pytest.mark.parametrize("role", ["intake_clerk", "reviewer"])
    def test_demo_reset_denied(self, client, role):
        resp = client.post(
            "/api/v1/demo/reset",
            headers={"X-GovDoc-Role": role},
        )
        assert resp.status_code == 403

    # Meta endpoints — no auth required
    def test_meta_roles_no_auth(self, client):
        resp = client.get("/api/v1/meta/roles")
        assert resp.status_code == 200

    def test_meta_departments_no_auth(self, client):
        resp = client.get("/api/v1/meta/departments")
        assert resp.status_code == 200

    def test_meta_prompt_versions_no_auth(self, client):
        resp = client.get("/api/v1/meta/prompt-versions")
        assert resp.status_code == 200
