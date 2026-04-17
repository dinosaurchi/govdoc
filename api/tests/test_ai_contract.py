"""Contract tests for AI schemas, config loading, helpers, and prompt templates per §18.2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.adapters.modelstudio.schemas import (
    ClassificationResult,
    EmbeddingResult,
    EscalationResult,
    OCRResult,
    RerankResult,
    RoutingResult,
    SummaryResult,
)
from app.adapters.modelstudio.helpers import strip_json_fences

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
# Schema contract tests
# ===========================================================================


class TestClassificationResultSchema:
    """Contract tests for ClassificationResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
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
    def test_missing_doc_type_rejected(self):
        payload = {
            "confidence": 0.5,
            "rationale": "test",
            "urgency": "normal",
            "confidentiality": "unclassified",
        }
        with pytest.raises(Exception):
            ClassificationResult(**payload)

    @pytest.mark.contract
    def test_confidence_out_of_range_rejected(self):
        payload = {
            "doc_type": "cong_van",
            "confidence": 1.5,
            "rationale": "test",
        }
        with pytest.raises(Exception):
            ClassificationResult(**payload)

    @pytest.mark.contract
    def test_defaults(self):
        result = ClassificationResult(doc_type="other", confidence=0.5, rationale="test")
        assert result.urgency == "normal"
        assert result.confidentiality == "unclassified"
        assert result.issuing_agency is None


class TestSummaryResultSchema:
    """Contract tests for SummaryResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
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

    @pytest.mark.contract
    def test_missing_suggested_department_rejected(self):
        payload = {
            "routing_confidence": 0.5,
            "routing_rationale": "test",
        }
        with pytest.raises(Exception):
            RoutingResult(**payload)


class TestEscalationResultSchema:
    """Contract tests for EscalationResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
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

    @pytest.mark.contract
    def test_missing_primary_recommendation_rejected(self):
        payload = {
            "alternatives": [],
            "ambiguity_explanation": "test",
            "confidence_per_department": {},
            "final_confidence": 0.5,
            "needs_consultation": False,
        }
        with pytest.raises(Exception):
            EscalationResult(**payload)

    @pytest.mark.contract
    def test_missing_alternatives_rejected(self):
        payload = {
            "primary_recommendation": "phong_hanh_chinh",
            "ambiguity_explanation": "test",
            "confidence_per_department": {},
            "final_confidence": 0.5,
            "needs_consultation": False,
        }
        with pytest.raises(Exception):
            EscalationResult(**payload)


class TestOCRResultSchema:
    """Contract tests for OCRResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        payload = {
            "text": "Sample OCR text output",
            "page_count": 1,
        }
        result = OCRResult(**payload)
        assert result.text == "Sample OCR text output"

    @pytest.mark.contract
    def test_defaults(self):
        result = OCRResult(text="hello")
        assert result.extraction_method == "qwen-ocr"
        assert result.warnings == []
        assert result.page_count == 1


class TestEmbeddingResultSchema:
    """Contract tests for EmbeddingResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        payload = {
            "embedding": [0.1, 0.2, 0.3],
            "model": "text-embedding-v4",
            "total_tokens": 10,
        }
        result = EmbeddingResult(**payload)
        assert len(result.embedding) == 3

    @pytest.mark.contract
    def test_embedding_is_list_of_float(self):
        result = EmbeddingResult(embedding=[1, 2, 3], model="test", total_tokens=5)
        assert all(isinstance(x, float) for x in result.embedding)


class TestRerankResultSchema:
    """Contract tests for RerankResult Pydantic model."""

    @pytest.mark.contract
    def test_valid_payload_parses(self):
        payload = {
            "index": 0,
            "relevance_score": 0.95,
            "text": "doc1",
        }
        result = RerankResult(**payload)
        assert result.index == 0
        assert result.relevance_score == 0.95
        assert result.text == "doc1"


# ===========================================================================
# strip_json_fences tests per §17.12
# ===========================================================================


class TestStripJsonFences:
    """Contract tests for JSON fence stripping helper."""

    @pytest.mark.contract
    def test_plain_json_unchanged(self):
        assert strip_json_fences('{"a": 1}') == '{"a": 1}'

    @pytest.mark.contract
    def test_json_with_language_tag(self):
        input_str = '```json\n{"a":1}\n```'
        assert strip_json_fences(input_str) == '{"a":1}'

    @pytest.mark.contract
    def test_json_without_language_tag(self):
        input_str = '```\n{"a":1}\n```'
        assert strip_json_fences(input_str) == '{"a":1}'

    @pytest.mark.contract
    def test_surrounding_whitespace_stripped(self):
        input_str = '  \n {"a":1} \n '
        assert strip_json_fences(input_str) == '{"a":1}'

    @pytest.mark.contract
    def test_garbage_returned_unchanged(self):
        assert strip_json_fences("garbage") == "garbage"

    @pytest.mark.contract
    def test_nested_backticks_in_string_literal(self):
        input_str = '```json\n{"a": "```nested```"}\n```'
        result = strip_json_fences(input_str)
        assert '"a": "```nested```"' in result


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
    def test_roles_yaml_has_four_roles(self):
        yaml = pytest.importorskip("yaml")
        with open(_CONFIG_DIR / "roles.yaml") as f:
            data = yaml.safe_load(f)
        roles = data.get("roles", {})
        assert set(roles.keys()) == {"intake_clerk", "reviewer", "consultant", "supervisor"}

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
