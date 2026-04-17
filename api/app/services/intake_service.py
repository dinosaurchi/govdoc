"""Real intake: validate upload, persist file, call extraction interface (mock provider)."""

import hashlib
import os
import re
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import (
    Document,
    DocumentFile,
    DocumentStatus,
    ExtractionMethod,
    ExtractedArtifact,
    SecurityLevel,
    Urgency,
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
    role_id: str,
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

    doc_title = (title or "").strip() or _safe_filename(upload.filename)
    doc = Document(
        title=doc_title,
        status=DocumentStatus.received,
        security_level=SecurityLevel.unclassified,
        urgency=Urgency.normal,
    )
    db.add(doc)
    db.flush()

    root = Path(settings.LOCAL_FILE_STORAGE_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    dest_dir = root / str(doc.id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(upload.filename)
    storage_key = str(Path(str(doc.id)) / safe_name)
    abs_path = root / storage_key

    with open(abs_path, "wb") as f:
        f.write(body)

    sha = hashlib.sha256(body).hexdigest()

    dfile = DocumentFile(
        document_id=doc.id,
        storage_key=storage_key,
        original_filename=safe_name,
        mime_type=mime,
        size_bytes=size,
        sha256=sha,
    )
    db.add(dfile)
    db.flush()

    extracted_text = await extractor.extract_text(str(abs_path))

    artifact = ExtractedArtifact(
        document_id=doc.id,
        extraction_method=ExtractionMethod.plaintext,
        text=extracted_text,
    )
    db.add(artifact)

    write_audit_event(
        db,
        document_id=doc.id,
        actor_role=role_id,
        event_type="INTAKE_UPLOAD",
        metadata_json={
            "original_filename": safe_name,
            "mime_type": mime,
            "size_bytes": size,
            "sha256": sha,
            "extraction_method": "plaintext",
        },
    )

    db.commit()
    db.refresh(doc)
    return doc
