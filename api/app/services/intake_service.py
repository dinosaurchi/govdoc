import uuid

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentFile, ExtractedArtifact, DocumentStatus
from app.services.storage import LocalFileStorage
from app.services.extraction.real_extractor import RealExtractor
from app.services.file_validation import validate_file, FileValidationError
from app.services.audit_service import write_audit_event


class IntakeService:
    def __init__(self, db: Session):
        self.db = db
        self.storage = LocalFileStorage()
        self.extractor = RealExtractor()

    def intake(
        self,
        filename: str,
        content: bytes,
        mime_type: str | None,
        role_id: str,
        ai_provider=None,
        prompt_registry=None,
    ) -> dict:
        """Process file upload: validate, store, extract, optionally run AI analysis.

        Parameters
        ----------
        ai_provider : AIProvider | None
            If provided and extraction succeeds with text, runs the AI analysis
            pipeline (classify → summarize → route → optional escalate).
            On AI failure the document is still created with extracted text; its
            status is set to ``analysis_failed``.
        """
        document_id = str(uuid.uuid4())

        # Validate file
        try:
            validated_mime = validate_file(filename, content, mime_type)
        except FileValidationError:
            raise

        # Create document record
        document = Document(
            id=document_id,
            title=filename,
            status=DocumentStatus.received,
        )
        self.db.add(document)
        write_audit_event(self.db, document_id=document_id, actor_role=role_id, event_type="document.created")

        # Save file
        file_meta = self.storage.save(document_id, filename, content)
        doc_file = DocumentFile(
            id=str(uuid.uuid4()),
            document_id=document_id,
            storage_key=file_meta["storage_key"],
            original_filename=filename,
            mime_type=validated_mime,
            size_bytes=file_meta["size_bytes"],
            sha256=file_meta["sha256"],
            is_primary=True,
        )
        self.db.add(doc_file)

        # Extract text
        try:
            full_path = str(self.storage.root / file_meta["storage_key"])
            result = self.extractor.extract_text(full_path, filename, validated_mime)
            document.status = DocumentStatus.extracted
            write_audit_event(
                self.db,
                document_id=document_id,
                actor_role=role_id,
                event_type="extraction.completed",
                metadata_json={"method": result.method.value, "pages": result.page_count},
            )
        except Exception as e:
            document.status = DocumentStatus.ingest_failed
            write_audit_event(
                self.db,
                document_id=document_id,
                actor_role=role_id,
                event_type="extraction.failed",
                metadata_json={"error": str(e)},
            )
            self.db.flush()
            raise

        # ── OCR fallback for scan PDFs / images ──────────────────────
        # If primary extraction yielded no usable text and we have an AI
        # provider, render the file and run OCR through the provider.
        # Fail-fast: any OCR error aborts intake (no silent empty-text fall).
        needs_ocr = (
            ai_provider is not None
            and not self.extractor.has_text(result)
            and (
                validated_mime == "application/pdf"
                or validated_mime.startswith("image/")
            )
        )
        if needs_ocr:
            try:
                result = self.extractor.extract_with_ocr(
                    full_path, validated_mime, ai_provider.ocr
                )
                write_audit_event(
                    self.db,
                    document_id=document_id,
                    actor_role=role_id,
                    event_type="extraction.ocr",
                    metadata_json={"method": result.method.value, "pages": result.page_count},
                )
            except Exception as e:
                document.status = DocumentStatus.ingest_failed
                write_audit_event(
                    self.db,
                    document_id=document_id,
                    actor_role=role_id,
                    event_type="extraction.failed",
                    metadata_json={"error": str(e)},
                )
                self.db.flush()
                raise

        # Create artifact
        artifact = ExtractedArtifact(
            id=str(uuid.uuid4()),
            document_id=document_id,
            extraction_method=result.method,
            text=result.text,
            page_count=result.page_count,
            warnings=result.warnings,
        )
        self.db.add(artifact)

        # ── AI analysis (optional, graceful degradation) ──────────────
        ai_analyses = []
        if ai_provider is not None and result.text:
            from app.services.ai.analysis_service import AnalysisService

            analysis_svc = AnalysisService(self.db, ai_provider, prompt_registry=prompt_registry)
            try:
                ai_analyses = analysis_svc.analyze_document(
                    document,
                    result.text,
                    role_id,
                )
            except Exception as e:
                document.status = DocumentStatus.analysis_failed
                write_audit_event(
                    self.db,
                    document_id=document_id,
                    actor_role=role_id,
                    event_type="analysis.failed",
                    metadata_json={"error": str(e)},
                )
                self.db.flush()
                # Don't raise — document is still created with extracted text

        self.db.flush()
        return {"document": document, "file": doc_file, "artifact": artifact, "ai_analyses": ai_analyses}
