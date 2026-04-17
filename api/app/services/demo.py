from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from app.repositories import system as sys_repo
from app.models.document import (
    AIAnalysis,
    Document,
    DocumentFile,
    DocumentType,
    ExtractedArtifact,
    WorkflowState,
)
from app.core.config import settings


class DemoService:
    def __init__(self, db: Session):
        self.db = db

    async def seed_baseline(self):
        roles = ["Intake Clerk", "Department Reviewer", "Consultant", "Supervisor"]
        for r_name in roles:
            existing = sys_repo.role.get_multi(self.db, limit=100)
            if not any(r.name == r_name for r in existing):
                sys_repo.role.create(
                    self.db, obj_in={"name": r_name, "description": f"Standard {r_name} role"}
                )

        depts = [
            {"name": "Văn phòng Bộ", "code": "VP"},
            {"name": "Vụ Kế hoạch - Tài chính", "code": "KHTC"},
            {"name": "Vụ Khoa học và Công nghệ", "code": "KHCN"},
            {"name": "Vụ Pháp chế", "code": "PC"},
            {"name": "Cục Công nghiệp", "code": "CN"},
        ]
        for d_info in depts:
            existing = sys_repo.department.get_multi(self.db, limit=100)
            if not any(d.code == d_info["code"] for d in existing):
                sys_repo.department.create(self.db, obj_in=d_info)

    def _attach_placeholder_file_and_artifact(self, doc: Document) -> None:
        root = Path(settings.LOCAL_FILE_STORAGE_ROOT)
        root.mkdir(parents=True, exist_ok=True)
        storage_rel = f"{doc.id}/seed-placeholder.txt"
        dest = root / storage_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = "Seeded placeholder content for GovDoc baseline.\n"
        dest.write_text(text, encoding="utf-8")
        sz = dest.stat().st_size

        df = DocumentFile(
            document_id=doc.id,
            file_name="seed-placeholder.txt",
            mime_type="text/plain",
            file_size_bytes=sz,
            storage_relative_path=storage_rel,
            sha256_hex=None,
        )
        self.db.add(df)
        self.db.flush()

        art = ExtractedArtifact(
            document_id=doc.id,
            document_file_id=df.id,
            extraction_method="mock_seed",
            extraction_source_label="DemoSeed",
            extracted_text="[Seed placeholder] Mock extracted text for seeded scenario.",
            structured_metadata_json={"seed": True},
        )
        self.db.add(art)

    async def seed_scenarios(self) -> List[Document]:
        await self.seed_baseline()

        doc1 = Document(
            title="V/v Phê duyệt kế hoạch bảo trì hệ thống IT 2026",
            doc_type=DocumentType.cong_van,
            state=WorkflowState.assigned_to_department,
        )
        self.db.add(doc1)
        self.db.flush()
        self._attach_placeholder_file_and_artifact(doc1)
        self.db.add(
            AIAnalysis(
                document_id=doc1.id,
                suggested_type="công văn",
                urgency_score=2,
                summary="Seeded hero scenario — mock AI summary for closeout demo.",
                suggested_department="Văn phòng Bộ",
                raw_response='{"mock": true, "seed": true}',
                analysis_source_label="mock_seed",
            )
        )

        doc2 = Document(
            title="Đề xuất điều chỉnh hạn mức ngân sách dự phòng",
            doc_type=DocumentType.to_trinh,
            state=WorkflowState.intake_received,
        )
        self.db.add(doc2)
        self.db.flush()
        self._attach_placeholder_file_and_artifact(doc2)

        doc3 = Document(
            title="Hợp đồng hợp tác quốc tế về chuyển giao công nghệ",
            doc_type=DocumentType.quyet_dinh,
            state=WorkflowState.consultation_requested,
        )
        self.db.add(doc3)
        self.db.flush()
        self._attach_placeholder_file_and_artifact(doc3)

        self.db.commit()
        self.db.refresh(doc1)
        self.db.refresh(doc2)
        self.db.refresh(doc3)
        return [doc1, doc2, doc3]
