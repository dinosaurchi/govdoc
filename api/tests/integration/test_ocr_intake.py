"""Integration test: OCR fallback wires through the intake pipeline."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app

pytest.importorskip("pdf2image")


def _make_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clerk_headers():
    return {"X-GovDoc-Role": "intake_clerk"}


@pytest.mark.mock_integration
class TestOCRFallbackIntake:
    def test_blank_pdf_triggers_ocr_then_analysis(self, client, clerk_headers):
        pdf_bytes = _make_blank_pdf()
        resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("scan.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        artifact = data.get("extracted_artifact")
        assert artifact is not None
        assert "Test OCR output" in artifact["text"]
        assert artifact["extraction_method"] == "render_ocr"

        analyses = data.get("ai_analyses", [])
        assert len(analyses) >= 3, f"Expected ≥3 analyses, got {len(analyses)}"
        stages = {a["stage"] for a in analyses}
        assert {"classify", "summarize", "route"}.issubset(stages)
