"""AI provider interface updated for Model Studio schemas."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.adapters.modelstudio.schemas import (
    ClassificationResult,
    EmbeddingResult,
    EscalationResult,
    OCRResult,
    RoutingResult,
    SummaryResult,
)


class AIProvider(ABC):
    @abstractmethod
    def classify(self, text: str, departments: list[dict] | None = None) -> ClassificationResult:
        pass

    @abstractmethod
    def summarize(self, text: str) -> SummaryResult:
        pass

    @abstractmethod
    def route(self, text: str, departments: list[dict]) -> RoutingResult:
        pass

    @abstractmethod
    def escalate(self, text: str, departments: list[dict]) -> EscalationResult:
        pass

    @abstractmethod
    def embed(self, texts: list[str]) -> list[EmbeddingResult]:
        pass

    @abstractmethod
    def ocr(self, image_base64: str) -> OCRResult:
        pass
