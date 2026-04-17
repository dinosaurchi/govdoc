"""Seed and demo data services."""

import hashlib
import uuid
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from app.models.system import Role, Department, DemoScenario
from app.models.document import (
    Document,
    DocumentFile,
    DocumentStatus,
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
# Demo scenario fixtures (real bundled hard-case PDFs)
# ---------------------------------------------------------------------------

# Each entry: stable scenario id → metadata + path relative to project root.
# Using stable ids keeps `seed_scenarios` idempotent across runs.
DEMO_SCENARIO_FIXTURES = [
    {
        "id": "hero-001",
        "name": "Hero — Incoming công văn",
        "description": "Standard incoming công văn, clean digital PDF — happy-path demo.",
        "category": "hero",
        "title": "Hero — Incoming công văn",
        "path": "data/incoming/cong-van/cong-van_quang-ngai_son-mai_dang-ky-mua-sam-xe-o-to.pdf",
    },
    {
        "id": "ambiguity-001",
        "name": "Ambiguity — multi-department công văn",
        "description": "Công văn touching multiple departments — exercises escalation flow.",
        "category": "ambiguity",
        "title": "Ambiguity — multi-department công văn",
        "path": "data/hard-cases/multi-department/01_cong-van_moj_y-kien-co-quan.pdf",
    },
    {
        "id": "scan-001",
        "name": "Scan — low-quality công văn",
        "description": "Scanned công văn (no embedded text) — exercises OCR fallback.",
        "category": "scan",
        "title": "Scan — low-quality công văn",
        "path": "data/hard-cases/scanned-low-quality/01_scan_cong-van_dong-nai_297_ubnd-ttpvhcc_p1.pdf",
    },
    {
        "id": "out-of-scope-001",
        "name": "Out-of-scope — lịch làm việc tuần",
        "description": "Internal weekly schedule — should be flagged out_of_scope by the model.",
        "category": "out_of_scope",
        "title": "Out-of-scope — lịch làm việc tuần",
        "path": "data/hard-cases/out-of-scope/04_thong-bao_hai-phong_lac-phuong_lich-lam-viec-tuan.pdf",
    },
]


# ---------------------------------------------------------------------------
# DemoService — for demo scenarios endpoint
# ---------------------------------------------------------------------------


class DemoService:
    def __init__(self, db: Session):
        self.db = db

    async def seed_baseline(self):
        """Seed roles and departments on startup."""
        seed_all(self.db)

    # ── Internal helpers ─────────────────────────────────────────────
    def _store_fixture_file(self, doc_id: str, src_path: Path) -> dict:
        """Copy a fixture PDF into LOCAL_FILE_STORAGE_ROOT.

        Returns dict with storage_key, sha256, size_bytes, original_filename.
        Fails fast if the source file is missing — we never silently substitute
        placeholder content.
        """
        if not src_path.exists():
            raise FileNotFoundError(f"Demo fixture not found: {src_path}")

        content = src_path.read_bytes()
        if not content:
            raise ValueError(f"Demo fixture is empty: {src_path}")

        root = Path(settings.LOCAL_FILE_STORAGE_ROOT)
        if not root.is_absolute():
            root = _PROJECT_ROOT / root
        original_filename = src_path.name
        storage_key = f"{doc_id}/{original_filename}"
        dest = root / storage_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)

        return {
            "storage_key": storage_key,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
            "original_filename": original_filename,
        }

    async def seed_scenarios(self) -> List[Document]:
        """Seed the four canonical demo scenarios using bundled hard-case PDFs.

        Idempotent: if a `DemoScenario` with the stable id already exists, skip
        creation entirely (we do not refresh files or re-create the document).
        Returns the list of `Document` rows for the *newly* created scenarios.
        """
        await self.seed_baseline()

        created: List[Document] = []

        for fixture in DEMO_SCENARIO_FIXTURES:
            existing = self.db.query(DemoScenario).filter_by(id=fixture["id"]).first()
            if existing:
                continue

            src_path = _PROJECT_ROOT / fixture["path"]
            doc_id = str(uuid.uuid4())

            file_meta = self._store_fixture_file(doc_id, src_path)

            doc = Document(
                id=doc_id,
                title=fixture["title"],
                status=DocumentStatus.received,
                security_level=SecurityLevel.unclassified,
                urgency=Urgency.normal,
            )
            self.db.add(doc)
            self.db.flush()

            doc_file = DocumentFile(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                storage_key=file_meta["storage_key"],
                original_filename=file_meta["original_filename"],
                mime_type="application/pdf",
                size_bytes=file_meta["size_bytes"],
                sha256=file_meta["sha256"],
                is_primary=True,
            )
            self.db.add(doc_file)

            scenario = DemoScenario(
                id=fixture["id"],
                name=fixture["name"],
                description=fixture["description"],
                document_id=doc.id,
                category=fixture["category"],
            )
            self.db.add(scenario)

            created.append(doc)

        self.db.commit()
        for doc in created:
            self.db.refresh(doc)
        return created

    # ── Optional live analysis pass ──────────────────────────────────
    def analyze_seeded(self, ai_provider, prompt_registry) -> List[Document]:
        """Run the full extract + analyze pipeline on every seeded scenario
        whose Document has no ExtractedArtifact yet.

        Uses the OCR fallback for scan PDFs. Fails fast on the first error so
        operators can see exactly which scenario broke.
        """
        from app.models.document import ExtractedArtifact, ExtractionMethod
        from app.services.ai.analysis_service import AnalysisService
        from app.services.audit_service import write_audit_event
        from app.services.extraction.real_extractor import RealExtractor
        from app.services.storage import LocalFileStorage

        extractor = RealExtractor()
        storage = LocalFileStorage()
        analysis_svc = AnalysisService(self.db, ai_provider, prompt_registry=prompt_registry)

        processed: List[Document] = []

        scenarios = self.db.query(DemoScenario).all()
        for scenario in scenarios:
            if not scenario.document_id:
                continue

            doc = self.db.query(Document).filter_by(id=scenario.document_id).first()
            if not doc:
                continue

            existing_artifact = (
                self.db.query(ExtractedArtifact)
                .filter_by(document_id=doc.id)
                .first()
            )
            if existing_artifact:
                continue

            doc_file = next((f for f in doc.files if f.is_primary), None) or (
                doc.files[0] if doc.files else None
            )
            if not doc_file:
                raise FileNotFoundError(
                    f"Seeded scenario {scenario.id} has no file attached"
                )

            full_path = str(storage.root / doc_file.storage_key)
            result = extractor.extract_text(full_path, doc_file.original_filename, doc_file.mime_type)
            if not extractor.has_text(result):
                result = extractor.extract_with_ocr(full_path, doc_file.mime_type, ai_provider.ocr)

            artifact = ExtractedArtifact(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                extraction_method=result.method,
                text=result.text,
                page_count=result.page_count,
                warnings=result.warnings,
            )
            self.db.add(artifact)
            doc.status = DocumentStatus.extracted
            write_audit_event(
                self.db,
                document_id=doc.id,
                actor_role="supervisor",
                event_type="extraction.completed",
                metadata_json={"method": result.method.value, "pages": result.page_count},
            )

            analysis_svc.analyze_document(doc, result.text, role_id="supervisor")
            self.db.commit()
            self.db.refresh(doc)
            processed.append(doc)

        return processed
