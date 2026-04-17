"""Integration smoke for the retrieval/evidence path (Pass 7).

Ensures both the debug `/api/v1/retrieval/search` endpoint and the
document-scoped `/api/v1/documents/{id}/evidence` endpoint return
non-empty results when the retrieval service has reference chunks
and a `FakeAIProvider.embed` function wired in.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.retrieval.retrieval_service import RetrievalService
from fake_ai_provider import FakeAIProvider


REFERENCE_CHUNKS = [
    {
        "id": "ref-001",
        "text": "Nghị định 30/2020 quy định về công tác văn thư trong cơ quan hành chính nhà nước.",
        "source": "data/reference-corpus/legal-reference/01_nghi_dinh_30_2020_van_thu.md",
    },
    {
        "id": "ref-002",
        "text": "Luật Tiếp công dân 2013 quy định trách nhiệm tiếp nhận, xử lý khiếu nại tố cáo.",
        "source": "data/reference-corpus/legal-reference/03_luat_tiep_cong_dan_2013.md",
    },
    {
        "id": "ref-003",
        "text": "Quy trình cấp giấy phép xây dựng tại UBND cấp huyện theo Luật Xây dựng.",
        "source": "data/reference-corpus/legal-reference/stub.md",
    },
]


@pytest.fixture
def client_with_refs():
    """Client whose retrieval service has known chunks + fake embeddings."""
    with TestClient(app) as c:
        fake = FakeAIProvider()
        svc = RetrievalService(embed_fn=fake.embed, rerank_fn=None, reference_chunks=REFERENCE_CHUNKS)
        app.state.retrieval_service = svc
        yield c


@pytest.fixture
def clerk_headers():
    return {"X-GovDoc-Role": "intake_clerk"}


@pytest.mark.mock_integration
class TestRetrievalSearch:
    def test_search_returns_results(self, client_with_refs):
        resp = client_with_refs.post(
            "/api/v1/retrieval/search",
            json={"query": "công văn tiếp công dân", "top_k": 5},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "results" in data
        results = data["results"]
        assert len(results) > 0
        assert len(results) <= 5
        for item in results:
            assert "id" in item
            assert "text" in item
            assert "source" in item
            assert "score" in item

    def test_search_respects_top_k(self, client_with_refs):
        resp = client_with_refs.post(
            "/api/v1/retrieval/search",
            json={"query": "công văn", "top_k": 2},
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) <= 2


@pytest.mark.mock_integration
class TestDocumentEvidence:
    def test_evidence_endpoint_returns_results(self, client_with_refs, clerk_headers):
        # Upload a document so the evidence endpoint has an artifact to query on.
        content = b"This is a test document about cong van and tiep cong dan procedures."
        upload_resp = client_with_refs.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("evidence_test.txt", io.BytesIO(content), "text/plain")},
        )
        assert upload_resp.status_code == 200, upload_resp.text
        doc_id = upload_resp.json()["document"]["id"]

        resp = client_with_refs.get(
            f"/api/v1/documents/{doc_id}/evidence",
            headers=clerk_headers,
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["document_id"] == doc_id
        assert "results" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0
        for item in data["results"]:
            assert "id" in item
            assert "text" in item
            assert "source" in item
            assert "score" in item
