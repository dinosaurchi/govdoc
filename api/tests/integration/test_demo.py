"""Integration tests for demo seeding and reset readiness."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.document import Document, DocumentFile
from app.models.system import DemoScenario
from app.services.demo import DEMO_SCENARIO_FIXTURES, DemoService

# Demo fixtures live under the gitignored `data/` directory and are NOT shipped
# with the repo. Skip these tests entirely when the fixtures aren't present
# (e.g. on CI runners) — they are covered by local runs after `make seed-demo`.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_missing = [
    fx["path"]
    for fx in DEMO_SCENARIO_FIXTURES
    if not (_PROJECT_ROOT / fx["path"]).exists()
]
if _missing:
    pytest.skip(
        f"Demo fixtures not available (missing: {_missing[0]} …). "
        "Run `make seed-demo` locally to exercise these tests.",
        allow_module_level=True,
    )


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_scenarios():
    """Seed the four canonical demo scenarios; clean up after the test."""
    db = SessionLocal()
    try:
        svc = DemoService(db)
        asyncio.get_event_loop().run_until_complete(svc.seed_scenarios())
    finally:
        db.close()

    yield

    db = SessionLocal()
    try:
        scenarios = db.query(DemoScenario).all()
        doc_ids = [s.document_id for s in scenarios if s.document_id]
        db.query(DemoScenario).delete()
        if doc_ids:
            db.query(DocumentFile).filter(DocumentFile.document_id.in_(doc_ids)).delete(
                synchronize_session=False
            )
            db.query(Document).filter(Document.id.in_(doc_ids)).delete(
                synchronize_session=False
            )
        db.commit()
    finally:
        db.close()

@pytest.mark.mock_integration
class TestDemoScenarios:
    def test_seed_creates_four_scenarios(self, client, seeded_scenarios):
        resp = client.get("/api/v1/demo/scenarios")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) == 4

        categories = {row["category"] for row in data}
        assert categories == {"hero", "ambiguity", "scan", "out_of_scope"}

        for row in data:
            assert row["document_id"] is not None
            assert row["name"]

    def test_seed_is_idempotent(self, client, seeded_scenarios):
        db = SessionLocal()
        try:
            svc = DemoService(db)
            asyncio.get_event_loop().run_until_complete(svc.seed_scenarios())
        finally:
            db.close()

        resp = client.get("/api/v1/demo/scenarios")
        assert resp.status_code == 200
        assert len(resp.json()) == 4

    def test_demo_reset_builds_ready_scenarios(self, client):
        reset = client.post(
            "/api/v1/demo/reset",
            headers={"X-GovDoc-Role": "supervisor"},
        )
        assert reset.status_code == 200, reset.text
        payload = reset.json()
        assert payload["message"] == "Demo data reset successfully"
        assert len(payload["documents"]) == 4

        resp = client.get("/api/v1/demo/scenarios")
        assert resp.status_code == 200, resp.text
        scenarios = resp.json()
        assert len(scenarios) == 4

        docs_by_category = {}
        for row in scenarios:
            doc_id = row["document_id"]
            assert doc_id
            detail = client.get(
                f"/api/v1/documents/{doc_id}",
                headers={"X-GovDoc-Role": "intake_clerk"},
            )
            assert detail.status_code == 200, detail.text
            docs_by_category[row["category"]] = detail.json()

        hero = docs_by_category["hero"]
        assert hero["status"] == "analyzed"
        assert len(hero["artifacts"]) == 1
        assert {item["stage"] for item in hero["analyses"]} >= {"classify", "summarize", "route"}
        assert hero["routing_decisions"][0]["final_department_id"] == "phong_tai_chinh"

        ambiguity = docs_by_category["ambiguity"]
        assert ambiguity["status"] == "analyzed"
        ambiguity_route = next(item for item in ambiguity["analyses"] if item["stage"] == "route")
        route_confidence = ambiguity_route["payload_json"]["routing_confidence"]
        assert route_confidence is not None
        if route_confidence < 0.7:
            assert ambiguity_route["payload_json"]["secondary_department"]
            ambiguity_escalate = next(
                item for item in ambiguity["analyses"] if item["stage"] == "escalate"
            )
            assert ambiguity_escalate["payload_json"]["needs_consultation"] is True

        scan = docs_by_category["scan"]
        assert scan["status"] == "analyzed"
        assert scan["artifacts"][0]["extraction_method"] in {"render_ocr", "qwen-ocr"}
        assert scan["artifacts"][0]["text"]

        out_of_scope = docs_by_category["out_of_scope"]
        assert out_of_scope["status"] == "out_of_scope"
