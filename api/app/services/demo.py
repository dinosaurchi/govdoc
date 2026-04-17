"""Seed and demo data services."""

import hashlib
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from app.models.system import Role, Department, DemoScenario
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
from app.core.config_loader import load_roles_config

# Resolve paths relative to the project root regardless of CWD
# demo.py is at: api/app/services/demo.py  → 3 parents up = api/ , 4 = project root
_API_ROOT = Path(__file__).resolve().parent.parent.parent  # api/
_PROJECT_ROOT = _API_ROOT.parent  # govdoc/


# ---------------------------------------------------------------------------
# Default departments
# ---------------------------------------------------------------------------

DEFAULT_DEPARTMENTS = [
    {"id": "phong_hanh_chinh", "name": "Phòng Hành chính", "description": "Administrative affairs"},
    {"id": "phong_ke_hoach", "name": "Phòng Kế hoạch", "description": "Planning department"},
    {"id": "phong_tai_chinh", "name": "Phòng Tài chính", "description": "Finance department"},
    {"id": "phong_phap_che", "name": "Phòng Pháp chế", "description": "Legal department"},
    {"id": "phong_ke_hoach_dau_tu", "name": "Phòng Kế hoạch Đầu tư", "description": "Investment planning"},
]


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------


def seed_roles(db: Session):
    """Seed roles from roles.yaml config."""
    config_path = _PROJECT_ROOT / settings.ROLES_CONFIG_PATH
    config = load_roles_config(config_path)
    for role_id, role_data in config["roles"].items():
        existing = db.query(Role).filter_by(id=role_id).first()
        if not existing:
            role = Role(
                id=role_id,
                label=role_data["label"],
                allowed_actions=role_data.get("allowed_actions", []),
            )
            db.add(role)
    db.commit()


def seed_departments(db: Session):
    """Seed departments from default list."""
    for dept_data in DEFAULT_DEPARTMENTS:
        existing = db.query(Department).filter_by(id=dept_data["id"]).first()
        if not existing:
            dept = Department(
                id=dept_data["id"],
                name=dept_data["name"],
                description=dept_data.get("description"),
            )
            db.add(dept)
    db.commit()


def seed_all(db: Session):
    """Seed all base data: roles and departments."""
    seed_roles(db)
    seed_departments(db)


# ---------------------------------------------------------------------------
# DemoService — for demo scenarios endpoint
# ---------------------------------------------------------------------------


class DemoService:
    def __init__(self, db: Session):
        self.db = db

    async def seed_baseline(self):
        """Seed roles and departments on startup."""
        seed_all(self.db)

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
