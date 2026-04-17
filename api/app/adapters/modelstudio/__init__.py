"""Alibaba Model Studio client, rerank, schemas, helpers, and credential probes."""

from app.adapters.modelstudio.client import (
    AIAuthError,
    AIModelUnavailableError,
    AIRateLimitError,
    AISchemaInvalidError,
    ModelStudioClient,
    ModelStudioError,
)
from app.adapters.modelstudio.credentials import probe_live_credentials
from app.adapters.modelstudio.helpers import strip_json_fences
from app.adapters.modelstudio.rerank_client import RerankClient
from app.adapters.modelstudio.schemas import (
    ClassificationResult,
    EmbeddingResult,
    EscalationResult,
    OCRResult,
    RerankResult,
    RoutingResult,
    SummaryResult,
)

__all__ = [
    "AIAuthError",
    "AIModelUnavailableError",
    "AIRateLimitError",
    "AISchemaInvalidError",
    "ClassificationResult",
    "EmbeddingResult",
    "EscalationResult",
    "ModelStudioClient",
    "ModelStudioError",
    "OCRResult",
    "RerankClient",
    "RerankResult",
    "RoutingResult",
    "SummaryResult",
    "probe_live_credentials",
    "strip_json_fences",
]
