"""Analysis orchestrator — runs classify → summarize → route (+ optional escalate) pipeline."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.document import (
    AIAnalysis,
    AnalysisSource,
    AnalysisStage,
    Document,
    DocumentStatus,
    ExtractedArtifact,
    RoutingDecision,
    SecurityLevel,
    Urgency,
)
from app.models.system import Department
from app.services.ai.interface import AIProvider
from app.services.audit_service import write_audit_event
from app.services.workflow import InvalidTransitionError, validate_transition

ROUTING_CONFIDENCE_THRESHOLD = 0.7  # Below this, trigger escalation


class AnalysisService:
    """Orchestrates the AI analysis pipeline for a document."""

    def __init__(self, db: Session, ai_provider: AIProvider, prompt_registry=None):
        self.db = db
        self.ai = ai_provider
        self.prompt_registry = prompt_registry

    def analyze_document(
        self,
        document: Document,
        text: str,
        role_id: str,
        force: bool = False,
    ) -> list[AIAnalysis]:
        """Run full analysis pipeline: classify → summarize → route (+ optional escalate).

        Returns list of persisted AIAnalysis records.
        """
        analyses: list[AIAnalysis] = []

        # Get departments for routing/escalation
        departments = [{"id": d.id, "name": d.name} for d in self.db.query(Department).all()]

        # ── Stage 1: Classify ──────────────────────────────────────────
        classify_result = self.ai.classify(text, departments)
        classify_analysis = self._persist_analysis(
            document.id,
            AnalysisStage.classify,
            classify_result,
            role_id,
        )
        analyses.append(classify_analysis)

        # Update document fields from classification
        document.issuing_agency = classify_result.issuing_agency or document.issuing_agency
        try:
            if classify_result.urgency in [e.value for e in Urgency]:
                document.urgency = Urgency(classify_result.urgency)
            if classify_result.confidentiality in [e.value for e in SecurityLevel]:
                document.security_level = SecurityLevel(classify_result.confidentiality)
        except ValueError:
            pass  # Keep defaults if invalid values

        # ── Stage 2: Summarize ─────────────────────────────────────────
        summary_result = self.ai.summarize(text)
        summary_analysis = self._persist_analysis(
            document.id,
            AnalysisStage.summarize,
            summary_result,
            role_id,
        )
        analyses.append(summary_analysis)

        # ── Stage 3: Route ─────────────────────────────────────────────
        route_result = self.ai.route(text, departments)
        route_analysis = self._persist_analysis(
            document.id,
            AnalysisStage.route,
            route_result,
            role_id,
        )
        analyses.append(route_analysis)

        # Create routing decision record
        routing_decision = RoutingDecision(
            id=str(uuid.uuid4()),
            document_id=document.id,
            suggested_department_id=route_result.suggested_department,
            decided_by_role=None,  # Will be updated on human review
            decision="accepted",
            rationale=route_result.routing_rationale,
        )
        self.db.add(routing_decision)

        # ── Stage 4: Escalate (conditional) ────────────────────────────
        needs_escalation = (
            route_result.routing_confidence < ROUTING_CONFIDENCE_THRESHOLD
            or route_result.needs_supervisor_review
            or route_result.needs_consultation
        )

        if needs_escalation:
            escalate_result = self.ai.escalate(text, departments)
            escalate_analysis = self._persist_analysis(
                document.id,
                AnalysisStage.escalate,
                escalate_result,
                role_id,
            )
            analyses.append(escalate_analysis)

        # ── Transition document status ─────────────────────────────────
        try:
            validate_transition(document.status, DocumentStatus.analyzed)
            document.status = DocumentStatus.analyzed
        except InvalidTransitionError:
            pass  # Keep current status if transition not allowed

        self.db.flush()
        return analyses

    def re_analyze(
        self,
        document: Document,
        role_id: str,
        force: bool = False,
    ) -> list[AIAnalysis]:
        """Re-analyze document (idempotent per prompt version).

        Fetches text from the latest extracted artifact and re-runs the
        analysis pipeline unless results already exist at the current prompt
        version and *force* is False.
        """
        artifact = (
            self.db.query(ExtractedArtifact)
            .filter(ExtractedArtifact.document_id == document.id)
            .order_by(ExtractedArtifact.extracted_at.desc())
            .first()
        )

        if not artifact or not artifact.text:
            raise ValueError("No extracted text available for analysis")

        # Idempotency check (skip if already analyzed at current prompt version)
        if not force and self.prompt_registry:
            current_version = self.prompt_registry.get_prompt_version("classify")
            if current_version:
                existing = (
                    self.db.query(AIAnalysis)
                    .filter(
                        AIAnalysis.document_id == document.id,
                        AIAnalysis.prompt_version == current_version,
                    )
                    .all()
                )
                existing_stages = {a.stage for a in existing}
                expected_stages = {
                    AnalysisStage.classify,
                    AnalysisStage.summarize,
                    AnalysisStage.route,
                }
                if expected_stages.issubset(existing_stages):
                    return existing

        return self.analyze_document(document, artifact.text, role_id, force=force)

    # ── Private helpers ────────────────────────────────────────────────

    def _persist_analysis(
        self,
        document_id: str,
        stage: AnalysisStage,
        result,
        role_id: str,
    ) -> AIAnalysis:
        """Persist an AI analysis result and write an audit event."""
        prompt_version = self.prompt_registry.get_prompt_version(stage.value) if self.prompt_registry else "unknown"

        model_name = self._get_model_for_stage(stage)

        analysis = AIAnalysis(
            id=str(uuid.uuid4()),
            document_id=document_id,
            stage=stage,
            model_name=model_name,
            prompt_version=prompt_version,
            source=AnalysisSource.live,
            payload_json=result.model_dump(),
            confidence=getattr(result, "confidence", None),
        )
        self.db.add(analysis)

        write_audit_event(
            self.db,
            document_id=document_id,
            actor_role=role_id,
            event_type="ai.call",
            metadata_json={
                "stage": stage.value,
                "model": model_name,
                "prompt_version": prompt_version,
            },
        )
        return analysis

    def _get_model_for_stage(self, stage: AnalysisStage) -> str:
        """Look up the model name for a given analysis stage from config."""
        from app.core.config import settings
        from app.core.config_loader import load_models_config

        config_path = _resolve_project_root() / settings.MODELS_CONFIG_PATH
        config = load_models_config(config_path)
        stage_map = {
            AnalysisStage.classify: "classify",
            AnalysisStage.summarize: "summarize",
            AnalysisStage.route: "route",
            AnalysisStage.escalate: "escalate",
        }
        key = stage_map.get(stage, "classify")
        return config["models"][key]["model"]


def _resolve_project_root():
    from pathlib import Path

    # analysis_service.py is at: api/app/services/ai/analysis_service.py
    return Path(__file__).resolve().parent.parent.parent.parent.parent
