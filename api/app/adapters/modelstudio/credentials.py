"""
Model Studio credential validation.

Live API probing is intentionally NOT implemented in Pass 3 baseline.
`make check-credentials` validates the env contract, then fails with an explicit
message until `probe_live_credentials` is wired to the real OpenAPI-compatible
Model Studio endpoints in a later coding-agent pass.

TODO: Implement minimal generation/embed/OCR probes per govdoc_implementation_plan.md
using typed request/response models and normalized errors.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence


class LiveCredentialProbeNotImplementedError(RuntimeError):
    """Raised when a live Model Studio round-trip is required but not yet implemented."""


REQUIRED_FOR_PROBE: Sequence[str] = (
    "MODELSTUDIO_API_KEY",
    "MODELSTUDIO_BASE_URL",
    "MODELSTUDIO_DASHSCOPE_URL",
)


@dataclass(frozen=True)
class EnvValidationResult:
    missing: tuple[str, ...]


def validate_probe_env() -> EnvValidationResult:
    """Return missing required variables (empty tuple if all present and non-empty)."""
    missing: list[str] = []
    for key in REQUIRED_FOR_PROBE:
        val = os.environ.get(key)
        if val is None or not str(val).strip():
            missing.append(key)
    return EnvValidationResult(missing=tuple(missing))


def probe_live_credentials() -> None:
    """
    Perform a minimal live credential check against Model Studio.

    **Not implemented** in the Pass 3 baseline: callers must treat this as a
    hard failure until real HTTP probes are added alongside the production adapter.
    """
    raise LiveCredentialProbeNotImplementedError(
        "Live Model Studio credential probe is not implemented yet. "
        "Env validation passed; implement probe_live_credentials() in "
        "api/app/adapters/modelstudio/credentials.py and wire httpx calls to the "
        "documented Model Studio OpenAPI-compatible endpoints (generation, embedding, OCR)."
    )
