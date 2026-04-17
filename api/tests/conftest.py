"""Pytest configuration, markers, and shared fixtures per §18.1."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures path – make fixtures importable / discoverable
# ---------------------------------------------------------------------------
_FIXTURES_DIR = Path(__file__).parent / "fixtures"
if str(_FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(_FIXTURES_DIR))


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
