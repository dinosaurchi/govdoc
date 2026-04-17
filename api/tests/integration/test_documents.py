import io
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app.main import app


def _make_blank_pdf() -> bytes:
    """Create a minimal blank PDF (no embedded text)."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def _make_text_file(content: str = "Test document content for GovDoc SecureFlow.") -> bytes:
    return content.encode("utf-8")


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def clerk_headers():
    return {"X-GovDoc-Role": "intake_clerk"}


@pytest.fixture
def reviewer_headers():
    return {"X-GovDoc-Role": "reviewer"}


@pytest.mark.mock_integration
class TestDocumentUpload:
    def test_upload_text_file_creates_records(self, client, clerk_headers):
        content = _make_text_file("This is a test document for GovDoc SecureFlow intake pipeline.")
        resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "document" in data
        assert data["document"]["title"] == "test.txt"
        assert data["document"]["status"] in ("extracted", "analyzed")
        assert data["extracted_artifact"] is not None
        assert "test document" in data["extracted_artifact"]["text"].lower()

    def test_upload_pdf_creates_records(self, client, clerk_headers):
        pdf_bytes = _make_blank_pdf()
        resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["document"]["title"] == "test.pdf"
        assert data["document"]["status"] in ("extracted", "analyzed")

    def test_upload_empty_file_rejected(self, client, clerk_headers):
        resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert resp.status_code == 400
        detail = resp.json()
        assert detail["error"]["code"] == "CORRUPT_FILE"

    def test_upload_unsupported_mime_rejected(self, client, clerk_headers):
        resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("test.exe", io.BytesIO(b"binary content here"), "application/x-msdownload")},
        )
        assert resp.status_code == 400
        detail = resp.json()
        assert detail["error"]["code"] == "UNSUPPORTED_MIME"

    def test_upload_missing_role_header(self, client):
        content = _make_text_file()
        resp = client.post(
            "/api/v1/documents/",
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 400


@pytest.mark.mock_integration
class TestDocumentList:
    def test_list_documents_empty(self, client, clerk_headers):
        resp = client.get("/api/v1/documents/", headers=clerk_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_documents_after_upload(self, client, clerk_headers):
        content = _make_text_file("List test document content for GovDoc.")
        client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("list_test.txt", io.BytesIO(content), "text/plain")},
        )
        resp = client.get("/api/v1/documents/", headers=clerk_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for doc in data:
            assert "consultation_notes" in doc
            assert isinstance(doc["consultation_notes"], list)

    def test_list_documents_with_status_filter(self, client, clerk_headers):
        resp = client.get("/api/v1/documents/?status=analyzed", headers=clerk_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for doc in data:
            assert doc["status"] == "analyzed"


@pytest.mark.mock_integration
class TestDocumentDetail:
    def test_get_document_detail(self, client, clerk_headers):
        content = _make_text_file("Detail test document content for GovDoc.")
        upload_resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("detail_test.txt", io.BytesIO(content), "text/plain")},
        )
        assert upload_resp.status_code == 200
        doc_id = upload_resp.json()["document"]["id"]

        resp = client.get(f"/api/v1/documents/{doc_id}", headers=clerk_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == doc_id
        assert "files" in data
        assert "artifacts" in data
        assert len(data["files"]) >= 1
        assert len(data["artifacts"]) >= 1

    def test_get_document_not_found(self, client, clerk_headers):
        resp = client.get("/api/v1/documents/nonexistent-id", headers=clerk_headers)
        assert resp.status_code == 404


@pytest.mark.mock_integration
class TestDocumentFileDownload:
    def test_download_file(self, client, clerk_headers):
        content = _make_text_file("Download test document content for GovDoc.")
        upload_resp = client.post(
            "/api/v1/documents/",
            headers=clerk_headers,
            files={"file": ("download_test.txt", io.BytesIO(content), "text/plain")},
        )
        doc_id = upload_resp.json()["document"]["id"]

        resp = client.get(f"/api/v1/documents/{doc_id}/file", headers=clerk_headers)
        assert resp.status_code == 200
        assert resp.content == content

    def test_download_file_not_found(self, client, clerk_headers):
        resp = client.get("/api/v1/documents/nonexistent-id/file", headers=clerk_headers)
        assert resp.status_code == 404
