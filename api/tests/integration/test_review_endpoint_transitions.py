from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.document import (
    ConsultationNote,
    Document,
    DocumentStatus,
    RoutingDecision,
)


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

    def test_resolve_consultation_keeps_status_while_other_notes_open(
        self, client: TestClient
    ):
        """Parallel consultations: resolving one of two open notes must keep
        the document on `in_consultation` until every note is handled."""
        document_id = _create_document(client)
        note_a_id = str(uuid.uuid4())
        note_b_id = str(uuid.uuid4())

        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).one()
            document.status = DocumentStatus.in_consultation
            db.add_all(
                [
                    ConsultationNote(
                        id=note_a_id,
                        document_id=document_id,
                        author_role="reviewer",
                        target_role="consultant",
                        body="Note A",
                    ),
                    ConsultationNote(
                        id=note_b_id,
                        document_id=document_id,
                        author_role="reviewer",
                        target_role="consultant",
                        body="Note B",
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        first = client.post(
            f"/api/v1/documents/{document_id}/resolve-consultation/{note_a_id}",
            headers={"X-GovDoc-Role": "consultant"},
        )
        assert first.status_code == 200, first.text
        assert first.json()["document"]["status"] == "in_consultation"
        assert first.json()["consultation_note"]["resolved_at"] is not None

        second = client.post(
            f"/api/v1/documents/{document_id}/resolve-consultation/{note_b_id}",
            headers={"X-GovDoc-Role": "consultant"},
        )
        assert second.status_code == 200, second.text
        assert second.json()["document"]["status"] == "under_review"

    def test_resolve_consultation_is_idempotent_for_already_resolved_notes(
        self, client: TestClient
    ):
        """Re-resolving an already-resolved note is a 400 — no silent retry."""
        document_id = _create_document(client)
        note_id = str(uuid.uuid4())

        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).one()
            document.status = DocumentStatus.in_consultation
            db.add(
                ConsultationNote(
                    id=note_id,
                    document_id=document_id,
                    author_role="reviewer",
                    target_role="consultant",
                    body="Already done",
                )
            )
            db.commit()
        finally:
            db.close()

        first = client.post(
            f"/api/v1/documents/{document_id}/resolve-consultation/{note_id}",
            headers={"X-GovDoc-Role": "consultant"},
        )
        assert first.status_code == 200

        retry = client.post(
            f"/api/v1/documents/{document_id}/resolve-consultation/{note_id}",
            headers={"X-GovDoc-Role": "consultant"},
        )
        assert retry.status_code == 400
        assert retry.json()["detail"]["error"]["code"] == "INVALID_TRANSITION"

    def test_approve_routing_copies_suggested_dept_onto_document(
        self, client: TestClient
    ):
        """Accepting the AI routing suggestion must actually set
        `document.assigned_department_id` and `routing_decision.final_department_id`.
        Regression for the bug that left docs stuck on under_review with no owner.
        """
        # _create_document triggers the AI analysis pipeline which persists
        # a RoutingDecision(suggested_department_id=..., final_department_id=None).
        # approve-routing must finalize that record onto the document.
        document_id = _create_document(client)
        _set_document_status(document_id, DocumentStatus.analyzed)

        db = SessionLocal()
        try:
            ai_rd = (
                db.query(RoutingDecision)
                .filter(RoutingDecision.document_id == document_id)
                .order_by(RoutingDecision.created_at.desc())
                .first()
            )
            assert ai_rd is not None, "AI pipeline should have persisted a routing suggestion"
            suggested = ai_rd.suggested_department_id
            assert suggested, "AI routing suggestion must have a department"
            assert ai_rd.final_department_id is None
        finally:
            db.close()

        response = client.post(
            f"/api/v1/documents/{document_id}/approve-routing",
            headers={"X-GovDoc-Role": "reviewer"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()["document"]
        assert payload["status"] == "routed"
        assert payload["assigned_department_id"] == suggested

        db = SessionLocal()
        try:
            rd = (
                db.query(RoutingDecision)
                .filter(RoutingDecision.document_id == document_id)
                .order_by(RoutingDecision.created_at.desc())
                .first()
            )
            assert rd is not None
            assert rd.final_department_id == suggested
            assert rd.decided_by_role == "reviewer"
        finally:
            db.close()

    def test_approve_routing_rejects_missing_ai_suggestion(
        self, client: TestClient
    ):
        """If no AI routing suggestion exists, approve-routing must refuse
        rather than silently putting the doc on `routed` with no owner."""
        document_id = _create_document(client)

        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).one()
            document.status = DocumentStatus.analyzed
            # Purge any AI-generated routing decisions to simulate the
            # "no suggestion available" case.
            db.query(RoutingDecision).filter(
                RoutingDecision.document_id == document_id
            ).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

        response = client.post(
            f"/api/v1/documents/{document_id}/approve-routing",
            headers={"X-GovDoc-Role": "reviewer"},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "NO_AI_ROUTING"

    def test_approve_from_under_review(self, client: TestClient):
        document_id = _create_document(client)
        _set_document_status(document_id, DocumentStatus.under_review)

        response = client.post(
            f"/api/v1/documents/{document_id}/approve",
            headers={"X-GovDoc-Role": "reviewer"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["document"]["status"] == "approved"

    def test_approve_rejects_with_open_consultation_notes(self, client: TestClient):
        document_id = _create_document(client)
        note_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == document_id).one()
            document.status = DocumentStatus.under_review
            db.add(
                ConsultationNote(
                    id=note_id,
                    document_id=document_id,
                    author_role="reviewer",
                    target_role="consultant",
                    body="Still open",
                )
            )
            db.commit()
        finally:
            db.close()

        response = client.post(
            f"/api/v1/documents/{document_id}/approve",
            headers={"X-GovDoc-Role": "reviewer"},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "OPEN_CONSULTATION_NOTES"

    def test_close_requires_approved_status(self, client: TestClient):
        document_id = _create_document(client)
        _set_document_status(document_id, DocumentStatus.under_review)

        bad = client.post(
            f"/api/v1/documents/{document_id}/close",
            headers={"X-GovDoc-Role": "supervisor"},
        )
        assert bad.status_code == 400
        assert bad.json()["detail"]["error"]["code"] == "INVALID_TRANSITION"

        _set_document_status(document_id, DocumentStatus.approved)
        good = client.post(
            f"/api/v1/documents/{document_id}/close",
            headers={"X-GovDoc-Role": "supervisor"},
        )
        assert good.status_code == 200, good.text
        assert good.json()["document"]["status"] == "closed"
