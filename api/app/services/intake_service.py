"""Real intake: validate upload, persist file, call extraction interface (mock provider)."""

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.role_util import get_role_id_by_name
from app.core.config import settings
from app.models.document import (
    Document,
    DocumentFile,
    DocumentType,
    ExtractedArtifact,
    WorkflowState,
)
from app.services.audit_service import write_audit_event
from app.services.extraction.interface import ExtractionProviderInterface


def _safe_filename(name: str) -> str:
    base = os.path.basename(name)
    return re.sub(r"[^a-zA-Z0-9._-]", "_", base) or "upload.bin"


async def process_document_upload(
    db: Session,
    *,
    upload: UploadFile,
    title: str | None,
    doc_type: DocumentType,
    role_name: str,
    extractor: ExtractionProviderInterface,
) -> Document:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Missing filename on upload")

    body = await upload.read()
    size = len(body)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file upload")
    if size > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size ({settings.MAX_UPLOAD_BYTES} bytes)",
        )

    mime = upload.content_type or "application/octet-stream"
    if mime not in settings.ALLOWED_UPLOAD_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported MIME type: {mime}. Allowed: {settings.ALLOWED_UPLOAD_MIME_TYPES}",
        )

    actor_id = get_role_id_by_name(db, role_name)

    doc_title = (title or "").strip() or _safe_filename(upload.filename)
    doc = Document(
        title=doc_title,
        doc_type=doc_type,
        state=WorkflowState.intake_received,
    )
    db.add(doc)
    db.flush()

    root = Path(settings.LOCAL_FILE_STORAGE_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    dest_dir = root / str(doc.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(upload.filename)
    storage_rel = str(Path(str(doc.id)) / safe_name)
    abs_path = root / storage_rel

    with open(abs_path, "wb") as f:
        f.write(body)

    sha = hashlib.sha256(body).hexdigest()

    dfile = DocumentFile(
        document_id=doc.id,
        file_name=safe_name,
        mime_type=mime,
        file_size_bytes=size,
        storage_relative_path=storage_rel,
        sha256_hex=sha,
    )
    db.add(dfile)
    db.flush()

    extracted_text = await extractor.extract_text(str(abs_path))
    structured = await extractor.extract_structured_data(str(abs_path))
    src = getattr(type(extractor), "source_label", None) or getattr(
        extractor, "source_label", None
    )
    source_label = src or type(extractor).__name__

    artifact = ExtractedArtifact(
        document_id=doc.id,
        document_file_id=dfile.id,
        extraction_method="mock_deterministic",
        extraction_source_label=source_label,
        extracted_text=extracted_text,
        structured_metadata_json=structured,
    )
    db.add(artifact)

    write_audit_event(
        db,
        document_id=doc.id,
        actor_role_id=actor_id,
        action="INTAKE_UPLOAD",
        details={
            "file_name": safe_name,
            "mime_type": mime,
            "bytes": size,
            "sha256": sha,
            "extraction_method": "mock_deterministic",
        },
    )

    db.refresh(doc)
    return doc
