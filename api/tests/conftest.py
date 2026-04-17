"""Pytest configuration, markers, and shared fixtures per §18.1."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Test isolation from live AI — set placeholder MODELSTUDIO_* env vars BEFORE
# `app.core.config.Settings` is first imported, so `validate_ai_config()`
# passes during app lifespan in tests. Real credentials (via .env) remain
# the source of truth in production.
# ---------------------------------------------------------------------------
os.environ.setdefault("MODELSTUDIO_API_KEY", "sk-test-placeholder")
os.environ.setdefault("MODELSTUDIO_BASE_URL", "https://test.invalid/compatible-mode/v1")
os.environ.setdefault("MODELSTUDIO_DASHSCOPE_URL", "https://test.invalid/api/v1")

# ---------------------------------------------------------------------------
# Fixtures path – make fixtures importable / discoverable
# ---------------------------------------------------------------------------
_FIXTURES_DIR = Path(__file__).parent / "fixtures"
if str(_FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(_FIXTURES_DIR))


# ---------------------------------------------------------------------------
# Test isolation from live AI: override the real provider with a fake and
# stub `RealAIProvider` in `app.main` so the lifespan does not hit Model
# Studio when constructing the retrieval service. Live tests (marked
# `live` / `live_integration`) opt out via --live.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _override_ai_provider(monkeypatch, request):
    if "live" in [m.name for m in request.node.iter_markers()] or "live_integration" in [
        m.name for m in request.node.iter_markers()
    ]:
        yield
        return

    from app.api import deps
    from app.main import app
    from app.services.retrieval.retrieval_service import RetrievalService
    from fake_ai_provider import FakeAIProvider

    fake = FakeAIProvider()
    app.dependency_overrides[deps.get_ai_provider] = lambda: fake

    # Replace lifespan-instantiated retrieval service (which would construct
    # RealAIProvider) with one wired to the fake embed function.
    original_lifespan = app.router.lifespan_context

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _patched_lifespan(_app):
        import app.main as _main

        monkeypatch.setattr(_main, "RealAIProvider", lambda: fake)
        async with original_lifespan(_app):
            _app.state.retrieval_service = RetrievalService(embed_fn=fake.embed, rerank_fn=None)
            yield

    app.router.lifespan_context = _patched_lifespan
    try:
        yield
    finally:
        app.dependency_overrides.pop(deps.get_ai_provider, None)
        app.router.lifespan_context = original_lifespan


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Enable live Model Studio API tests (requires credentials)",
    )
    parser.addoption(
        "--creds",
        action="store_true",
        default=False,
        help="Enable credential validation tests",
    )
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Enable full live integration tests (requires --live and credentials)",
    )


# ---------------------------------------------------------------------------
# Marker registration
# ---------------------------------------------------------------------------
markers = {
    "unit": "Fast, isolated unit tests (no external API)",
    "contract": "Schema / contract tests (no external API, always run in CI)",
    "mock_integration": "App-level integration with stubbed adapters (no external API, always run in CI)",
    "live": "Live Model Studio API tests (requires --live flag and credentials)",
    "creds": "Credential validation tests (requires --creds flag)",
    "live_integration": "Full pipeline with real Model Studio API (requires --integration flag)",
}


def pytest_configure(config: pytest.Config) -> None:
    for name, description in markers.items():
        config.addinivalue_line("markers", f"{name}: {description}")


# ---------------------------------------------------------------------------
# Gate-keeping: skip gated markers when flags are absent
# ---------------------------------------------------------------------------
_GATED_MARKERS = {
    "live": "--live",
    "creds": "--creds",
    "live_integration": "--integration",
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for marker_name, cli_flag in _GATED_MARKERS.items():
        if config.getoption(cli_flag, default=False):
            continue  # flag present – do not skip
        skip = pytest.mark.skip(reason=f"Needs {cli_flag} flag")
        for item in items:
            if marker_name in [m.name for m in item.iter_markers()]:
                item.add_marker(skip)
