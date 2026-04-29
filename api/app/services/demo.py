"""Seed and demo data services."""

import hashlib
import shutil
import uuid
from pathlib import Path
from typing import List

from sqlalchemy.orm import Session

from app.models.system import Role, Department, DemoScenario, AuditEvent, PromptVersion
from app.models.document import (
    AIAnalysis,
    AnalysisSource,
    AnalysisStage,
    Document,
    DocumentFile,
    DocumentStatus,
    ExtractedArtifact,
    RoutingDecision,
    RoutingDecisionType,
    SecurityLevel,
    Urgency,
    ConsultationNote,
)
from app.core.config import settings
from app.core.config_loader import load_roles_config
from app.services.audit_service import write_audit_event
from app.services.workflow import validate_transition

# Resolve paths relative to the project root regardless of CWD
# demo.py is at: api/app/services/demo.py  → 3 parents up = api/ , 4 = project root
_API_ROOT = Path(__file__).resolve().parent.parent.parent  # api/
_PROJECT_ROOT = _API_ROOT.parent  # govdoc/
_PACKAGED_DEMO_DATA_ROOT = Path("/app/demo-data")


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


DEMO_WORKFLOW_PLANS = {
    "hero-001": {
        "department_id": "phong_tai_chinh",
        "assigned_reviewer_role": "reviewer",
        "routing_decision": RoutingDecisionType.accepted,
        "routing_rationale": "Procurement-related administrative request routed to Finance for final response preparation.",
        "final_status": DocumentStatus.analyzed,
    },
    "ambiguity-001": {
        "department_id": None,
        "assigned_reviewer_role": None,
        "routing_decision": None,
        "routing_rationale": None,
        "route_overrides": {
            "secondary_department": "phong_ke_hoach",
            "routing_confidence": 0.58,
            "routing_rationale": "The document spans legal interpretation and planning impact, so the route is ambiguous.",
            "needs_consultation": True,
            "needs_supervisor_review": True,
        },
        "escalation_overrides": {
            "primary_recommendation": "phong_phap_che",
            "alternatives": ["phong_ke_hoach"],
            "ambiguity_explanation": "Cross-department overlap requires legal review plus planning input before assignment.",
            "final_confidence": 0.58,
            "needs_consultation": True,
            "consultation_reason": "The document impacts both legal affairs and planning responsibilities.",
        },
        "final_status": DocumentStatus.analyzed,
    },
    "scan-001": {
        "department_id": None,
        "assigned_reviewer_role": None,
        "routing_decision": None,
        "routing_rationale": None,
        "final_status": DocumentStatus.analyzed,
    },
    "out-of-scope-001": {
        "department_id": None,
        "assigned_reviewer_role": "supervisor",
        "routing_decision": RoutingDecisionType.out_of_scope,
        "routing_rationale": "Document is an internal weekly schedule and falls outside the intake workflow scope.",
        "final_status": DocumentStatus.out_of_scope,
    },
}


# ---------------------------------------------------------------------------
# DemoService — for demo scenarios endpoint
# ---------------------------------------------------------------------------


class DemoService:
    def __init__(self, db: Session):
        self.db = db

    async def seed_baseline(self):
        """Seed roles and departments on startup."""
        seed_all(self.db)

    def reset_demo_state(self) -> None:
        """Delete documents, demo scenarios, and uploaded demo artifacts.

        This intentionally clears all workflow records so demo reset returns the
        app to a known state instead of layering seeded records on top of stale
        uploads from prior runs.
        """
        document_ids = [row[0] for row in self.db.query(Document.id).all()]

        self.db.query(ConsultationNote).delete(synchronize_session=False)
        self.db.query(RoutingDecision).delete(synchronize_session=False)
        self.db.query(AIAnalysis).delete(synchronize_session=False)
        self.db.query(ExtractedArtifact).delete(synchronize_session=False)
        self.db.query(DocumentFile).delete(synchronize_session=False)
        self.db.query(AuditEvent).delete(synchronize_session=False)
        self.db.query(DemoScenario).delete(synchronize_session=False)
        self.db.query(Document).delete(synchronize_session=False)
        self.db.query(Role).delete(synchronize_session=False)
        self.db.query(Department).delete(synchronize_session=False)
        self.db.query(PromptVersion).delete(synchronize_session=False)
        self.db.commit()

        root = Path(settings.LOCAL_FILE_STORAGE_ROOT)
        if not root.is_absolute():
            root = _PROJECT_ROOT / root
        for document_id in document_ids:
            candidate = root / document_id
            if candidate.exists():
                shutil.rmtree(candidate)

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

    def _resolve_fixture_path(self, relative_path: str) -> Path:
        candidate = _PROJECT_ROOT / relative_path
        if candidate.exists():
            return candidate

        relative = Path(relative_path)
        packaged = _PACKAGED_DEMO_DATA_ROOT / (
            relative.relative_to("data") if relative.parts and relative.parts[0] == "data" else relative
        )
        if packaged.exists():
            return packaged

        raise FileNotFoundError(f"Demo fixture not found: {candidate}")

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

            src_path = self._resolve_fixture_path(fixture["path"])
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
        from app.services.ai.analysis_service import AnalysisService
        from app.services.extraction.real_extractor import RealExtractor
        from app.services.storage import LocalFileStorage

        extractor = RealExtractor()
        storage_root = Path(settings.LOCAL_FILE_STORAGE_ROOT)
        if not storage_root.is_absolute():
            storage_root = _PROJECT_ROOT / storage_root
        storage = LocalFileStorage(str(storage_root))
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
            existing_analyses = (
                self.db.query(AIAnalysis)
                .filter_by(document_id=doc.id)
                .count()
            )
            if existing_artifact and existing_analyses >= 3:
                continue

            if existing_artifact:
                if not existing_artifact.text:
                    raise ValueError(f"Seeded scenario {scenario.id} has an empty extracted artifact")
                doc.status = DocumentStatus.extracted
                analysis_svc.analyze_document(doc, existing_artifact.text, role_id="supervisor")
            else:
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

    def stage_seeded_documents(self) -> List[Document]:
        """Normalize seeded scenarios into a realistic cross-page demo state."""
        scenarios = self.db.query(DemoScenario).all()
        docs_by_scenario: list[tuple[DemoScenario, str]] = []
        for scenario in scenarios:
            if not scenario.document_id:
                continue
            docs_by_scenario.append((scenario, scenario.document_id))

        doc_ids = [doc_id for _, doc_id in docs_by_scenario]
        if not doc_ids:
            return []

        self.db.query(ConsultationNote).filter(
            ConsultationNote.document_id.in_(doc_ids)
        ).delete(synchronize_session=False)
        self.db.query(RoutingDecision).filter(
            RoutingDecision.document_id.in_(doc_ids)
        ).delete(synchronize_session=False)
        self.db.query(AuditEvent).filter(
            AuditEvent.document_id.in_(doc_ids),
            AuditEvent.event_type.notin_(("ai.call", "extraction.completed")),
        ).delete(synchronize_session=False)
        self.db.flush()
        self.db.expire_all()

        staged: list[Document] = []
        for scenario, doc_id in docs_by_scenario:
            doc = self.db.query(Document).filter_by(id=doc_id).first()
            if not doc:
                continue
            if not doc.artifacts:
                raise ValueError(f"Seeded scenario {scenario.id} is missing extracted artifacts")
            if len(doc.analyses) < 3:
                raise ValueError(f"Seeded scenario {scenario.id} is missing AI analyses")

            plan = DEMO_WORKFLOW_PLANS.get(scenario.id)
            if not plan:
                continue

            doc.status = DocumentStatus.analyzed
            doc.assigned_department_id = None
            doc.assigned_reviewer_role = None
            self.db.flush()

            self._apply_workflow_plan(doc, plan)
            staged.append(doc)

        self.db.commit()
        for doc in staged:
            self.db.refresh(doc)
        return staged

    async def seed_demo_ready(self, ai_provider, prompt_registry) -> List[Document]:
        """Create files, run extract/analyze as needed, and stage a demo-ready workflow spread."""
        await self.seed_scenarios()
        self.analyze_seeded(ai_provider, prompt_registry)
        return self.stage_seeded_documents()

    async def reset_demo_ready(self, ai_provider, prompt_registry) -> List[Document]:
        """Fully reset and rebuild the demo data into a deterministic ready state."""
        self.reset_demo_state()
        await self.seed_baseline()
        return await self.seed_demo_ready(ai_provider, prompt_registry)

    def _apply_workflow_plan(self, doc: Document, plan: dict) -> None:
        department_id = plan["department_id"]
        reviewer_role = plan["assigned_reviewer_role"]
        decision = plan["routing_decision"]
        rationale = plan["routing_rationale"]
        final_status = plan["final_status"]

        if final_status == DocumentStatus.analyzed:
            self._apply_analysis_overrides(doc, plan)
            self._normalize_ai_routing(doc, department_id, reviewer_role, decision, rationale)
            self.db.flush()
            return

        self._transition_document(doc, DocumentStatus.routed, actor_role=reviewer_role)
        self.db.add(
            RoutingDecision(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                suggested_department_id=department_id,
                final_department_id=department_id,
                decided_by_role=reviewer_role,
                decision=decision,
                rationale=rationale,
            )
        )
        doc.assigned_department_id = department_id
        doc.assigned_reviewer_role = reviewer_role
        self.db.flush()

        if final_status == DocumentStatus.under_review:
            self._transition_document(doc, DocumentStatus.under_review, actor_role=reviewer_role)
            return

        if final_status == DocumentStatus.in_consultation:
            self._transition_document(doc, DocumentStatus.under_review, actor_role=reviewer_role)
            self._add_consultation_notes(doc.id, plan["consultation_notes"])
            self._transition_document(doc, DocumentStatus.in_consultation, actor_role=reviewer_role)
            return

        if final_status == DocumentStatus.closed:
            self._transition_document(doc, DocumentStatus.under_review, actor_role=reviewer_role)
            self._transition_document(doc, DocumentStatus.approved, actor_role="supervisor")
            self._transition_document(doc, DocumentStatus.closed, actor_role="supervisor")
            return

        if final_status == DocumentStatus.out_of_scope:
            self._transition_document(doc, DocumentStatus.out_of_scope, actor_role=reviewer_role)
            return

        raise ValueError(f"Unsupported demo final status: {final_status}")

    def _apply_analysis_overrides(self, doc: Document, plan: dict) -> None:
        for stage_name, override_key in (("route", "route_overrides"), ("escalate", "escalation_overrides")):
            overrides = plan.get(override_key)
            if not overrides:
                continue
            analysis = next((item for item in doc.analyses if item.stage.value == stage_name), None)
            if not analysis:
                route_analysis = next((item for item in doc.analyses if item.stage == AnalysisStage.route), None)
                if not route_analysis:
                    raise ValueError(f"Seeded scenario for {doc.id} is missing route analysis")
                analysis = AIAnalysis(
                    id=str(uuid.uuid4()),
                    document_id=doc.id,
                    stage=AnalysisStage(stage_name),
                    model_name=route_analysis.model_name,
                    prompt_version=route_analysis.prompt_version,
                    source=AnalysisSource.cached,
                    payload_json=dict(overrides),
                    confidence=overrides.get("final_confidence") or overrides.get("routing_confidence"),
                )
                self.db.add(analysis)
                doc.analyses.append(analysis)
                continue
            payload = dict(analysis.payload_json or {})
            payload.update(overrides)
            analysis.payload_json = payload
            analysis.confidence = payload.get("final_confidence") or payload.get("routing_confidence")

    def _normalize_ai_routing(
        self,
        doc: Document,
        department_id: str | None,
        reviewer_role: str | None,
        decision: RoutingDecisionType | None,
        rationale: str | None,
    ) -> None:
        latest_routing = None
        if doc.routing_decisions:
            latest_routing = max(
                doc.routing_decisions,
                key=lambda item: item.created_at.timestamp() if item.created_at else 0,
            )

        if latest_routing is None:
            route_analysis = next((item for item in doc.analyses if item.stage.value == "route"), None)
            route_payload = route_analysis.payload_json if route_analysis else {}
            latest_routing = RoutingDecision(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                suggested_department_id=route_payload.get("suggested_department"),
                final_department_id=None,
                decided_by_role=None,
                decision=decision or RoutingDecisionType.accepted,
                rationale=rationale or route_payload.get("routing_rationale"),
            )
            self.db.add(latest_routing)

        if latest_routing:
            latest_routing.final_department_id = department_id
            latest_routing.decided_by_role = reviewer_role
            if decision is not None:
                latest_routing.decision = decision
            if rationale is not None:
                latest_routing.rationale = rationale

        doc.assigned_department_id = department_id
        doc.assigned_reviewer_role = reviewer_role

    def _transition_document(self, doc: Document, target: DocumentStatus, *, actor_role: str) -> None:
        if doc.status == target:
            return
        validate_transition(doc.status, target)
        from_state = doc.status.value
        doc.status = target
        write_audit_event(
            self.db,
            document_id=doc.id,
            actor_role=actor_role,
            event_type="workflow.transition",
            from_state=from_state,
            to_state=target.value,
        )
        self.db.flush()

    def _add_consultation_notes(self, document_id: str, notes: list[dict]) -> None:
        for note in notes:
            self.db.add(
                ConsultationNote(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    author_role=note["author_role"],
                    target_role=note.get("target_role"),
                    body=note["body"],
                )
            )
        self.db.flush()
