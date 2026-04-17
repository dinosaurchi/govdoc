"""Contract tests for AI schemas, config loading, and prompt templates per §18.2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_API_ROOT = Path(__file__).resolve().parent.parent  # api/
_CONFIG_DIR = _API_ROOT / "config"
_PROMPTS_DIR = _API_ROOT / "prompts"
_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

_EXPECTED_MODEL_KEYS = {"classify", "summarize", "route", "escalate", "ocr", "embed", "rerank"}
_EXPECTED_PROMPT_FILES = {"classify.txt", "summarize.txt", "route.txt", "escalate.txt"}


# ===========================================================================
# Schema contract tests – depend on schemas module created in a later pass.
# These will gracefully skip if the module does not exist yet.
# ===========================================================================


class TestClassificationResultSchema:
    """Contract tests for ClassificationResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        ClassificationResult = mod.ClassificationResult
        payload = {
            "doc_type": "cong_van",
            "confidence": 0.95,
            "rationale": "Standard official letter",
            "issuing_agency": "So Noi vu",
            "urgency": "normal",
            "confidentiality": "unclassified",
        }
        result = ClassificationResult(**payload)
        assert result.doc_type == "cong_van"
        assert result.confidence == 0.95

    @pytest.mark.contract
    def test_invalid_doc_type_rejected(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        ClassificationResult = mod.ClassificationResult
        payload = {
            "doc_type": "invalid_type",
            "confidence": 0.5,
            "rationale": "test",
            "urgency": "normal",
            "confidentiality": "unclassified",
        }
        with pytest.raises(Exception):
            ClassificationResult(**payload)


class TestSummaryResultSchema:
    """Contract tests for SummaryResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        SummaryResult = mod.SummaryResult
        payload = {
            "summary_points": ["point 1", "point 2"],
            "key_subject": "Administrative procedures",
            "key_entities": ["UBND", "So Noi vu"],
        }
        result = SummaryResult(**payload)
        assert len(result.summary_points) == 2
        assert result.key_subject == "Administrative procedures"

    @pytest.mark.contract
    def test_missing_summary_points_rejected(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        SummaryResult = mod.SummaryResult
        payload = {
            "key_subject": "Test",
            "key_entities": [],
        }
        with pytest.raises(Exception):
            SummaryResult(**payload)


class TestRoutingResultSchema:
    """Contract tests for RoutingResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        RoutingResult = mod.RoutingResult
        payload = {
            "suggested_department": "phong_hanh_chinh",
            "secondary_department": None,
            "routing_confidence": 0.88,
            "routing_rationale": "Administrative matter",
            "needs_consultation": False,
            "needs_supervisor_review": False,
        }
        result = RoutingResult(**payload)
        assert result.suggested_department == "phong_hanh_chinh"
        assert result.secondary_department is None


class TestEscalationResultSchema:
    """Contract tests for EscalationResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        EscalationResult = mod.EscalationResult
        payload = {
            "primary_recommendation": "phong_hanh_chinh",
            "alternatives": ["phong_phap_che"],
            "ambiguity_explanation": "Overlapping jurisdictions",
            "confidence_per_department": {"phong_hanh_chinh": 0.6, "phong_phap_che": 0.4},
            "final_confidence": 0.6,
            "needs_consultation": True,
            "consultation_reason": "Cross-departmental issue",
        }
        result = EscalationResult(**payload)
        assert result.primary_recommendation == "phong_hanh_chinh"


class TestOCRResultSchema:
    """Contract tests for OCRResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        OCRResult = mod.OCRResult
        payload = {
            "extracted_text": "Sample OCR text output",
            "confidence": 0.92,
            "page_count": 1,
        }
        result = OCRResult(**payload)
        assert result.extracted_text == "Sample OCR text output"


class TestEmbeddingResultSchema:
    """Contract tests for EmbeddingResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        EmbeddingResult = mod.EmbeddingResult
        payload = {
            "embedding": [0.1, 0.2, 0.3],
            "dimensions": 3,
            "model": "text-embedding-v4",
        }
        result = EmbeddingResult(**payload)
        assert len(result.embedding) == 3


class TestRerankResultSchema:
    """Contract tests for RerankResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        mod = pytest.importorskip("app.adapters.modelstudio.schemas", reason="Not implemented yet")
        RerankResult = mod.RerankResult
        payload = {
            "results": [
                {"index": 0, "relevance_score": 0.95, "document": {"text": "doc1"}},
                {"index": 1, "relevance_score": 0.80, "document": {"text": "doc2"}},
            ],
        }
        result = RerankResult(**payload)
        assert len(result.results) == 2


# ===========================================================================
# Config loading tests
# ===========================================================================


class TestModelsConfig:
    """Contract tests for models.yaml configuration."""

    @pytest.mark.contract
    def test_models_yaml_exists(self):
        assert _CONFIG_DIR.joinpath("models.yaml").is_file(), "config/models.yaml must exist"

    @pytest.mark.contract
    def test_models_yaml_has_all_seven_keys(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "models.yaml") as f:
            data = yaml.safe_load(f)
        models = data.get("models", {})
        assert set(models.keys()) == _EXPECTED_MODEL_KEYS

    @pytest.mark.contract
    def test_models_yaml_correct_model_names(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "models.yaml") as f:
            data = yaml.safe_load(f)
        models = data["models"]
        expected_models = {
            "classify": "qwen-plus",
            "summarize": "qwen-plus",
            "route": "qwen-plus",
            "escalate": "qwen-max",
            "ocr": "qwen-vl-plus",
            "embed": "text-embedding-v4",
            "rerank": "qwen3-rerank",
        }
        for key, expected_model in expected_models.items():
            assert models[key]["model"] == expected_model, f"models[{key}].model should be {expected_model!r}"

    @pytest.mark.contract
    def test_classify_has_temperature_and_max_tokens(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "models.yaml") as f:
            data = yaml.safe_load(f)
        classify = data["models"]["classify"]
        assert "temperature" in classify
        assert "max_tokens" in classify
        assert isinstance(classify["temperature"], (int, float))
        assert isinstance(classify["max_tokens"], int)

    @pytest.mark.contract
    def test_embed_has_dimensions(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "models.yaml") as f:
            data = yaml.safe_load(f)
        embed = data["models"]["embed"]
        assert "dimensions" in embed
        assert embed["dimensions"] == 1024

    @pytest.mark.contract
    def test_rerank_has_top_n(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "models.yaml") as f:
            data = yaml.safe_load(f)
        rerank = data["models"]["rerank"]
        assert "top_n" in rerank
        assert rerank["top_n"] == 5


class TestRolesConfig:
    """Contract tests for roles.yaml configuration."""

    @pytest.mark.contract
    def test_roles_yaml_exists(self):
        assert _CONFIG_DIR.joinpath("roles.yaml").is_file(), "config/roles.yaml must exist"

    @pytest.mark.contract
    def test_roles_yaml_has_three_roles(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "roles.yaml") as f:
            data = yaml.safe_load(f)
        roles = data.get("roles", {})
        assert set(roles.keys()) == {"intake_clerk", "reviewer", "supervisor"}

    @pytest.mark.contract
    def test_supervisor_has_demo_reset(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "roles.yaml") as f:
            data = yaml.safe_load(f)
        supervisor_actions = data["roles"]["supervisor"]["allowed_actions"]
        assert "demo.reset" in supervisor_actions

    @pytest.mark.contract
    def test_intake_clerk_has_minimal_actions(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "roles.yaml") as f:
            data = yaml.safe_load(f)
        clerk_actions = data["roles"]["intake_clerk"]["allowed_actions"]
        assert "documents.create" in clerk_actions
        assert "documents.read" in clerk_actions
        assert "documents.list" in clerk_actions
        # Clerk should NOT have escalation or close
        assert "documents.escalate" not in clerk_actions
        assert "documents.close" not in clerk_actions


# ===========================================================================
# Prompt file tests
# ===========================================================================


class TestPromptFiles:
    """Contract tests for prompt template files."""

    @pytest.mark.contract
    def test_all_four_prompt_files_exist(self):
        for name in _EXPECTED_PROMPT_FILES:
            path = _PROMPTS_DIR / name
            assert path.is_file(), f"prompts/{name} must exist"

    @pytest.mark.contract
    def test_classify_prompt_has_text_placeholder(self):
        content = (_PROMPTS_DIR / "classify.txt").read_text()
        assert "{text}" in content

    @pytest.mark.contract
    def test_classify_prompt_mentions_doc_type(self):
        content = (_PROMPTS_DIR / "classify.txt").read_text()
        assert "doc_type" in content

    @pytest.mark.contract
    def test_classify_prompt_mentions_confidence(self):
        content = (_PROMPTS_DIR / "classify.txt").read_text()
        assert "confidence" in content

    @pytest.mark.contract
    def test_summarize_prompt_has_text_placeholder(self):
        content = (_PROMPTS_DIR / "summarize.txt").read_text()
        assert "{text}" in content

    @pytest.mark.contract
    def test_summarize_prompt_mentions_summary_points(self):
        content = (_PROMPTS_DIR / "summarize.txt").read_text()
        assert "summary_points" in content

    @pytest.mark.contract
    def test_route_prompt_has_text_and_departments_placeholders(self):
        content = (_PROMPTS_DIR / "route.txt").read_text()
        assert "{text}" in content
        assert "{departments}" in content

    @pytest.mark.contract
    def test_route_prompt_mentions_suggested_department(self):
        content = (_PROMPTS_DIR / "route.txt").read_text()
        assert "suggested_department" in content

    @pytest.mark.contract
    def test_escalate_prompt_has_text_placeholder(self):
        content = (_PROMPTS_DIR / "escalate.txt").read_text()
        assert "{text}" in content

    @pytest.mark.contract
    def test_escalate_prompt_mentions_primary_recommendation(self):
        content = (_PROMPTS_DIR / "escalate.txt").read_text()
        assert "primary_recommendation" in content

    @pytest.mark.contract
    def test_missing_prompt_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            (_PROMPTS_DIR / "nonexistent_prompt.txt").read_text()


# ===========================================================================
# Test fixtures validation
# ===========================================================================


class TestFixtures:
    """Contract tests for test fixture files."""

    @pytest.mark.contract
    def test_sample_cong_van_fixture_exists(self):
        assert _FIXTURES_DIR.joinpath("sample_cong_van.txt").is_file()

    @pytest.mark.contract
    def test_sample_cong_van_has_sufficient_content(self):
        content = _FIXTURES_DIR.joinpath("sample_cong_van.txt").read_text()
        assert len(content) >= 200, "sample_cong_van.txt should have at least 200 characters"

    @pytest.mark.contract
    def test_sample_departments_fixture_valid_json(self):
        with open(_FIXTURES_DIR / "sample_departments.json") as f:
            data = json.load(f)
        assert "departments" in data
        assert len(data["departments"]) == 5

    @pytest.mark.contract
    def test_sample_departments_has_expected_ids(self):
        with open(_FIXTURES_DIR / "sample_departments.json") as f:
            data = json.load(f)
        ids = {d["id"] for d in data["departments"]}
        assert "phong_hanh_chinh" in ids
        assert "phong_tai_chinh" in ids

    @pytest.mark.contract
    def test_malformed_ai_response_fixture_exists(self):
        assert _FIXTURES_DIR.joinpath("malformed_ai_response.txt").is_file()

    @pytest.mark.contract
    def test_malformed_ai_response_is_not_valid_json(self):
        content = _FIXTURES_DIR.joinpath("malformed_ai_response.txt").read_text()
        with pytest.raises(json.JSONDecodeError):
            json.loads(content)

    @pytest.mark.contract
    def test_white_png_fixture_exists(self):
        assert _FIXTURES_DIR.joinpath("white_10x10.png").is_file()

    @pytest.mark.contract
    def test_white_png_is_valid_png(self):
        content = _FIXTURES_DIR.joinpath("white_10x10.png").read_bytes()
        # PNG signature: \x89PNG\r\n\x1a\n
        assert content[:8] == b"\x89PNG\r\n\x1a\n"
