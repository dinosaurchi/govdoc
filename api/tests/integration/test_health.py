import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.mock_integration
def test_healthz_liveness():
    with TestClient(app) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


@pytest.mark.mock_integration
def test_readyz_readiness():
    with TestClient(app) as client:
        r = client.get("/readyz")
        assert r.status_code == 200
        assert r.json().get("status") == "ok"
