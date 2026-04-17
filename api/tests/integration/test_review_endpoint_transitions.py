from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.document import ConsultationNote, Document, DocumentStatus


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _create_document(client: TestClient) -> str:
    response = client.post(
        "/api/v1/documents/",
        files={"file": ("test.txt", b"Test document content", "text/plain")},
        headers={"X-GovDoc-Role": "intake_clerk"},
    )
    assert response.status_code == 200, response.text
    return response.json()["document"]["id"]


def _set_document_status(document_id: str, status: DocumentStatus) -> None:
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).one()
        document.status = status
        db.commit()
    finally:
        db.close()


@pytest.mark.mock_integration
class TestReviewEndpointTransitions:
    def test_reroute_rejects_closed_document(self, client: TestClient):
        document_id = _create_document(client)
        _set_document_status(document_id, DocumentStatus.closed)

        response = client.post(
            f"/api/v1/documents/{document_id}/reroute",
            json={"department_id": "phong_tai_chinh", "rationale": "Should fail"},
            headers={"X-GovDoc-Role": "reviewer"},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "INVALID_TRANSITION"

    def test_reroute_succeeds_for_under_review_document(self, client: TestClient):
        document_id = _create_document(client)
        _set_document_status(document_id, DocumentStatus.under_review)

        response = client.post(
            f"/api/v1/documents/{document_id}/reroute",
            json={"department_id": "phong_tai_chinh", "rationale": "Valid reroute"},
            headers={"X-GovDoc-Role": "reviewer"},
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["document"]["status"] == "routed"
        assert payload["document"]["assigned_department_id"] == "phong_tai_chinh"
        assert payload["routing_decision"]["final_department_id"] == "phong_tai_chinh"

    def test_resolve_consultation_rejects_closed_document(self, client: TestClient):
        document_id = _create_document(client)
        note_id = str(uuid.uuid4())

        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).one()
            document.status = DocumentStatus.closed
            db.add(
                ConsultationNote(
                    id=note_id,
                    document_id=document_id,
                    author_role="reviewer",
                    target_role="consultant",
                    body="Please advise",
                )
            )
            db.commit()
        finally:
            db.close()

        response = client.post(
            f"/api/v1/documents/{document_id}/resolve-consultation/{note_id}",
            headers={"X-GovDoc-Role": "consultant"},
        )

        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "INVALID_TRANSITION"
