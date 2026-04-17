"""Integration tests for /demo/scenarios after seeding real fixtures."""

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
