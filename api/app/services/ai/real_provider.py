"""Real AI provider using Model Studio adapter."""

from __future__ import annotations

from pathlib import Path

from app.adapters.modelstudio.client import ModelStudioClient
from app.adapters.modelstudio.rerank_client import RerankClient
from app.adapters.modelstudio.schemas import (
    ClassificationResult,
    EmbeddingResult,
    EscalationResult,
    OCRResult,
    RoutingResult,
    SummaryResult,
)
from app.core.config import settings
from app.core.config_loader import load_models_config
from app.services.ai.interface import AIProvider


class RealAIProvider(AIProvider):
    """AIProvider backed by Alibaba Model Studio (live API calls)."""

    def __init__(self):
        self.client = ModelStudioClient()
        self.rerank_client = RerankClient()
        # Resolve models config relative to project root
        config_path = _resolve_project_root() / settings.MODELS_CONFIG_PATH
        self.models_config = load_models_config(config_path)["models"]

    def classify(self, text: str, departments: list[dict] | None = None) -> ClassificationResult:
        config = self.models_config["classify"]
        prompt = self._load_prompt("classify").replace("{text}", text[:8000])
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat_completion_json(
            model=config["model"],
            messages=messages,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            response_model=ClassificationResult,
        )

    def summarize(self, text: str) -> SummaryResult:
        config = self.models_config["summarize"]
        prompt = self._load_prompt("summarize").replace("{text}", text[:8000])
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat_completion_json(
            model=config["model"],
            messages=messages,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            response_model=SummaryResult,
        )

    def route(self, text: str, departments: list[dict]) -> RoutingResult:
        config = self.models_config["route"]
        dept_str = "\n".join(f"- {d['id']}: {d['name']}" for d in departments)
        prompt = self._load_prompt("route").replace("{text}", text[:8000]).replace("{departments}", dept_str)
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat_completion_json(
            model=config["model"],
            messages=messages,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            response_model=RoutingResult,
        )

    def escalate(self, text: str, departments: list[dict]) -> EscalationResult:
        config = self.models_config["escalate"]
        dept_str = "\n".join(f"- {d['id']}: {d['name']}" for d in departments)
        prompt = self._load_prompt("escalate").replace("{text}", text[:8000]).replace("{departments}", dept_str)
        messages = [{"role": "user", "content": prompt}]
        return self.client.chat_completion_json(
            model=config["model"],
            messages=messages,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            response_model=EscalationResult,
        )

    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        config = self.models_config["embed"]
        return self.client.embeddings(texts, model=config["model"], dimensions=config["dimensions"])

    def ocr(self, image_base64: str) -> OCRResult:
        config = self.models_config["ocr"]
        return self.client.ocr(image_base64, model=config["model"])

    def _load_prompt(self, stage: str) -> str:
        prompt_file = _resolve_project_root() / settings.PROMPT_CONFIG_PATH / f"{stage}.txt"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        return prompt_file.read_text()


def _resolve_project_root() -> Path:
    """Resolve the project root directory (govdoc/)."""
    # real_provider.py is at: api/app/services/ai/real_provider.py
    return Path(__file__).resolve().parent.parent.parent.parent.parent
