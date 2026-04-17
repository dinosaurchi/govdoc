import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.mock_integration
def test_health_liveness():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json().get("status") == "healthy"


@pytest.mark.mock_integration
def test_health_readiness():
    with TestClient(app) as client:
        r = client.get("/health/ready")
        assert r.status_code == 200
        assert r.json().get("status") == "ready"
