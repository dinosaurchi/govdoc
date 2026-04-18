"""Demo sample PDF downloads — served via API for reliable MIME and proxy routing."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.unit
def test_demo_sample_file_returns_pdf() -> None:
    with TestClient(app) as client:
        r = client.get("/api/v1/demo/sample-files/sample-cong-van-dong-nai.pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert len(r.content) > 10_000
    assert r.content[:4] == b"%PDF"


@pytest.mark.unit
def test_demo_sample_file_unknown_name_404() -> None:
    with TestClient(app) as client:
        r = client.get("/api/v1/demo/sample-files/not-a-real-file.pdf")
    assert r.status_code == 404
