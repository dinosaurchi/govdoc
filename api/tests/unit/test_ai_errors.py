"""Error handling unit tests for Model Studio adapter per §18.7."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.modelstudio.client import (
    AIAuthError,
    AIModelUnavailableError,
    AIRateLimitError,
    AISchemaInvalidError,
    ModelStudioClient,
    ModelStudioError,
)


# ---------------------------------------------------------------------------
# Helpers – mock OpenAI client to avoid real API calls
# ---------------------------------------------------------------------------


def _make_client() -> ModelStudioClient:
    """Create a ModelStudioClient with mocked internals (no real API call)."""
    with patch("app.adapters.modelstudio.client.settings") as mock_settings:
        mock_settings.validate_ai_config = MagicMock()
        mock_settings.MODELSTUDIO_API_KEY = "test-key"
        mock_settings.MODELSTUDIO_BASE_URL = "https://fake.example.com/v1"
        with patch("app.adapters.modelstudio.client.OpenAI") as MockOpenAI:
            client = ModelStudioClient()
            client.client = MockOpenAI.return_value
            return client


# ---------------------------------------------------------------------------
# Tests: OpenAI error normalization
# ---------------------------------------------------------------------------


class TestAuthenticationError:
    @pytest.mark.unit
    def test_raises_ai_auth_error(self):
        import openai

        client = _make_client()
        error = openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401, headers={}),
            body=None,
        )
        client.client.chat.completions.create.side_effect = error

        with pytest.raises(AIAuthError, match="authentication failed"):
            client.chat_completion("qwen-plus", [{"role": "user", "content": "test"}])


class TestNotFoundError:
    @pytest.mark.unit
    def test_raises_ai_model_unavailable_error(self):
        import openai

        client = _make_client()
        error = openai.NotFoundError(
            message="Model not found",
            response=MagicMock(status_code=404, headers={}),
            body=None,
        )
        client.client.chat.completions.create.side_effect = error

        with pytest.raises(AIModelUnavailableError, match="not available"):
            client.chat_completion("qwen-plus", [{"role": "user", "content": "test"}])


class TestRateLimitError:
    @pytest.mark.unit
    def test_raises_ai_rate_limit_error(self):
        import openai

        client = _make_client()
        error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429, headers={}),
            body=None,
        )
        client.client.chat.completions.create.side_effect = error

        with pytest.raises(AIRateLimitError, match="Rate limited"):
            client.chat_completion("qwen-plus", [{"role": "user", "content": "test"}])


class TestGenericError:
    @pytest.mark.unit
    def test_raises_model_studio_error(self):
        client = _make_client()
        client.client.chat.completions.create.side_effect = RuntimeError("Something broke")

        with pytest.raises(ModelStudioError, match="Model Studio error"):
            client.chat_completion("qwen-plus", [{"role": "user", "content": "test"}])


# ---------------------------------------------------------------------------
# Tests: JSON parsing and schema validation
# ---------------------------------------------------------------------------


class TestSchemaInvalidError:
    @pytest.mark.unit
    def test_valid_json_wrong_schema(self):
        """Adapter returns valid JSON but wrong schema → AISchemaInvalidError."""
        from app.adapters.modelstudio.schemas import ClassificationResult

        client = _make_client()
        # Return valid JSON that doesn't match ClassificationResult
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"wrong_field": "value"})
        client.client.chat.completions.create.return_value = mock_response

        with pytest.raises(AISchemaInvalidError, match="doesn't match expected schema"):
            client.chat_completion_json(
                "qwen-plus",
                [{"role": "user", "content": "test"}],
                response_model=ClassificationResult,
            )

    @pytest.mark.unit
    def test_non_json_content(self):
        """Adapter returns non-JSON content → AISchemaInvalidError with JSONDecodeError."""
        client = _make_client()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not JSON at all"
        client.client.chat.completions.create.return_value = mock_response

        with pytest.raises(AISchemaInvalidError, match="invalid JSON"):
            client.chat_completion_json(
                "qwen-plus",
                [{"role": "user", "content": "test"}],
            )


# ---------------------------------------------------------------------------
# Tests: Rerank client errors
# ---------------------------------------------------------------------------


class TestRerankClientErrors:
    @pytest.mark.unit
    def test_rerank_401_error(self):
        """Rerank endpoint returns 401 → RuntimeError with status code."""
        from app.adapters.modelstudio.rerank_client import RerankClient

        with patch("app.adapters.modelstudio.rerank_client.settings") as mock_settings:
            mock_settings.validate_ai_config = MagicMock()
            mock_settings.MODELSTUDIO_API_KEY = "bad-key"
            mock_settings.MODELSTUDIO_DASHSCOPE_URL = "https://fake-dashscope.example.com"

            with patch("app.adapters.modelstudio.rerank_client.httpx.Client") as MockClient:
                mock_http = MockClient.return_value
                mock_response = MagicMock()
                mock_response.status_code = 401
                mock_response.text = "Unauthorized"
                mock_http.post.return_value = mock_response

                rc = RerankClient()
                rc.client = mock_http

                with pytest.raises(RuntimeError, match="401"):
                    rc.rerank("test query", ["test document"])

    @pytest.mark.unit
    def test_rerank_404_error(self):
        """Rerank endpoint returns 404 → RuntimeError with status code."""
        from app.adapters.modelstudio.rerank_client import RerankClient

        with patch("app.adapters.modelstudio.rerank_client.settings") as mock_settings:
            mock_settings.validate_ai_config = MagicMock()
            mock_settings.MODELSTUDIO_API_KEY = "test-key"
            mock_settings.MODELSTUDIO_DASHSCOPE_URL = "https://fake-dashscope.example.com"

            with patch("app.adapters.modelstudio.rerank_client.httpx.Client") as MockClient:
                mock_http = MockClient.return_value
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_response.text = "Not Found"
                mock_http.post.return_value = mock_response

                rc = RerankClient()
                rc.client = mock_http

                with pytest.raises(RuntimeError, match="404"):
                    rc.rerank("test query", ["test document"])
