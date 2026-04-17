"""OpenAI-compatible Model Studio client per §17."""

from __future__ import annotations

import json

from openai import OpenAI

from app.adapters.modelstudio.helpers import strip_json_fences
from app.adapters.modelstudio.schemas import (
    EmbeddingResult,
    OCRResult,
)
from app.core.config import settings


# ── Custom error types ────────────────────────────────────────────────────────


class ModelStudioError(Exception):
    """Base error for Model Studio."""

    pass


class AIAuthError(ModelStudioError):
    pass


class AIModelUnavailableError(ModelStudioError):
    pass


class AIRateLimitError(ModelStudioError):
    pass


class AISchemaInvalidError(ModelStudioError):
    pass


# ── Client ────────────────────────────────────────────────────────────────────


class ModelStudioClient:
    def __init__(self) -> None:
        settings.validate_ai_config()
        self.client = OpenAI(
            api_key=settings.MODELSTUDIO_API_KEY,
            base_url=settings.MODELSTUDIO_BASE_URL,
        )

    def chat_completion(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> str:
        """Send chat completion request and return content string."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            self._normalize_error(e)

    def chat_completion_json(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.1,
        max_tokens: int = 1024,
        response_model=None,
    ) -> dict | object:
        """Send chat completion, strip fences, parse JSON, validate with Pydantic model."""
        content = self.chat_completion(model, messages, temperature, max_tokens)
        clean = strip_json_fences(content)
        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError as e:
            raise AISchemaInvalidError(f"AI returned invalid JSON: {e}\nContent: {content[:500]}")

        if response_model:
            try:
                return response_model.model_validate(parsed)
            except Exception as e:
                raise AISchemaInvalidError(
                    f"AI response doesn't match expected schema: {e}\nParsed: {json.dumps(parsed)[:500]}"
                )

        return parsed

    def embeddings(
        self,
        texts: list[str],
        model: str = "text-embedding-v4",
        dimensions: int = 1024,
    ) -> list[EmbeddingResult]:
        """Generate embeddings for texts."""
        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts,
                dimensions=dimensions,
            )
            results: list[EmbeddingResult] = []
            for item in response.data:
                results.append(
                    EmbeddingResult(
                        embedding=item.embedding,
                        model=model,
                        total_tokens=response.usage.total_tokens if response.usage else 0,
                    )
                )
            return results
        except Exception as e:
            self._normalize_error(e)

    def ocr(self, image_base64: str, model: str = "qwen-vl-plus") -> OCRResult:
        """OCR an image using multimodal VL model."""
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}",
                        },
                    },
                    {
                        "type": "text",
                        "text": "Please extract all text from this image. Return only the extracted text.",
                    },
                ],
            }
        ]
        try:
            content = self.chat_completion(model, messages, temperature=0.0, max_tokens=2048)
            return OCRResult(text=content or "")
        except Exception as e:
            self._normalize_error(e)

    def _normalize_error(self, e: Exception) -> None:
        """Normalize OpenAI errors to internal error types."""
        err_type = type(e).__name__
        if "AuthenticationError" in err_type or "auth" in str(e).lower():
            raise AIAuthError(f"Model Studio authentication failed: {e}") from e
        elif "NotFoundError" in err_type or "not found" in str(e).lower():
            raise AIModelUnavailableError(f"Model not available: {e}") from e
        elif "RateLimitError" in err_type or "rate" in str(e).lower():
            raise AIRateLimitError(f"Rate limited: {e}") from e
        else:
            raise ModelStudioError(f"Model Studio error: {e}") from e
