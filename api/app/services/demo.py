import hashlib
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from app.repositories import system as sys_repo
from app.models.document import (
    AIAnalysis,
    AnalysisStage,
    AnalysisSource,
    Document,
    DocumentFile,
    DocumentStatus,
    ExtractionMethod,
    ExtractedArtifact,
    RoutingDecisionType,
    SecurityLevel,
    Urgency,
)
from app.core.config import settings


class DemoService:
    def __init__(self, db: Session):
        self.db = db

    async def seed_baseline(self):
        roles = [
            {
                "id": "intake_clerk",
                "label": "Intake Clerk",
                "allowed_actions": [
                    "documents.create",
                    "documents.read",
                    "documents.list",
                ],
            },
            {
                "id": "reviewer",
                "label": "Department Reviewer",
                "allowed_actions": [
                    "documents.read",
                    "documents.list",
                    "documents.review",
                ],
            },
            {
                "id": "consultant",
                "label": "Consultant",
                "allowed_actions": [
                    "documents.read",
                    "consultation.create",
                    "consultation.complete",
                ],
            },
            {
                "id": "supervisor",
                "label": "Supervisor",
                "allowed_actions": [
                    "documents.read",
                    "documents.list",
                    "documents.escalate",
                    "documents.close",
                    "demo.reset",
                ],
            },
        ]
        for r_info in roles:
            existing = sys_repo.role.get(self.db, id=r_info["id"])
            if not existing:
                sys_repo.role.create(self.db, obj_in=r_info)

        depts = [
            {"name": "Văn phòng Bộ", "description": "Office of the Ministry"},
            {"name": "Vụ Kế hoạch - Tài chính", "description": "Planning & Finance Department"},
            {"name": "Vụ Khoa học và Công nghệ", "description": "Science & Technology Department"},
            {"name": "Vụ Pháp chế", "description": "Legal Affairs Department"},
            {"name": "Cục Công nghiệp", "description": "Industry Bureau"},
        ]
        for d_info in depts:
            existing = sys_repo.department.get_multi(self.db, limit=100)
            if not any(d.name == d_info["name"] for d in existing):
                sys_repo.department.create(self.db, obj_in=d_info)

    def _attach_placeholder_file_and_artifact(self, doc: Document) -> None:
        root = Path(settings.LOCAL_FILE_STORAGE_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        storage_key = f"{doc.id}/seed-placeholder.txt"
        dest = root / storage_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = "Seeded placeholder content for GovDoc baseline.\n"
        dest.write_text(text, encoding="utf-8")
        sz = dest.stat().st_size
        sha = hashlib.sha256(text.encode()).hexdigest()

        df = DocumentFile(
            document_id=doc.id,
            storage_key=storage_key,
            original_filename="seed-placeholder.txt",
            mime_type="text/plain",
            size_bytes=sz,
            sha256=sha,
        )
        self.db.add(df)
        self.db.flush()

        art = ExtractedArtifact(
            document_id=doc.id,
            extraction_method=ExtractionMethod.plaintext,
            text="[Seed placeholder] Mock extracted text for seeded scenario.",
            warnings=[],
        )
        self.db.add(art)

    async def seed_scenarios(self) -> List[Document]:
        await self.seed_baseline()

        doc1 = Document(
            title="V/v Phê duyệt kế hoạch bảo trì hệ thống IT 2026",
            status=DocumentStatus.under_review,
            security_level=SecurityLevel.unclassified,
            urgency=Urgency.normal,
        )
        self.db.add(doc1)
        self.db.flush()
        self._attach_placeholder_file_and_artifact(doc1)
        self.db.add(
            AIAnalysis(
                document_id=doc1.id,
                stage=AnalysisStage.classify,
                model_name="mock_seed",
                prompt_version="seed001",
                source=AnalysisSource.cached,
                payload_json={"mock": True, "seed": True},
                confidence=0.95,
            )
        )

        doc2 = Document(
            title="Đề xuất điều chỉnh hạn mức ngân sách dự phòng",
            status=DocumentStatus.received,
            security_level=SecurityLevel.unclassified,
            urgency=Urgency.normal,
        )
        self.db.add(doc2)
        self.db.flush()
        self._attach_placeholder_file_and_artifact(doc2)

        doc3 = Document(
            title="Hợp đồng hợp tác quốc tế về chuyển giao công nghệ",
            status=DocumentStatus.in_consultation,
            security_level=SecurityLevel.confidential,
            urgency=Urgency.urgent,
        )
        self.db.add(doc3)
        self.db.flush()
        self._attach_placeholder_file_and_artifact(doc3)

        self.db.commit()
        self.db.refresh(doc1)
        self.db.refresh(doc2)
        self.db.refresh(doc3)
        return [doc1, doc2, doc3]
