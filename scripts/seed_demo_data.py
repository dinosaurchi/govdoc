#!/usr/bin/env python3
"""
Seed canonical demo scenarios from bundled hard-case PDFs.

Always runs the (idempotent) baseline + scenario seed. If the env var
GOVDOC_SEED_LIVE=1 is set AND Model Studio credentials are configured,
also runs the full extract + analyze pipeline on every seeded document
that does not yet have an ExtractedArtifact.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.core.config import settings  # noqa: E402
from app.core.config_loader import load_prompt_versions_config  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.demo import DemoService  # noqa: E402
from app.services.prompt_registry import PromptRegistry  # noqa: E402


def _build_prompt_registry(db) -> PromptRegistry:
    prompt_versions_path = ROOT / "api/config/prompt_versions.yaml"
    prompts_dir = ROOT / settings.PROMPT_CONFIG_PATH
    labels = load_prompt_versions_config(prompt_versions_path)
    registry = PromptRegistry(prompts_dir, db, labels)
    registry.register_all()
    return registry


async def main() -> None:
    db = SessionLocal()
    try:
        svc = DemoService(db)
        docs = await svc.seed_scenarios()
        print(f"seed_demo_data: created seeded documents: {[d.id for d in docs]}")

        if os.environ.get("GOVDOC_SEED_LIVE") != "1":
            print(
                "seed_demo_data: skipping live analysis — GOVDOC_SEED_LIVE=1 required"
            )
            return

        try:
            settings.validate_ai_config()
        except ValueError as exc:
            print(
                f"seed_demo_data: skipping live analysis — {exc}"
            )
            return

        from app.services.ai.real_provider import RealAIProvider

        provider = RealAIProvider()
        registry = _build_prompt_registry(db)
        analyzed = svc.analyze_seeded(provider, registry)
        print(
            f"seed_demo_data: ran live analysis on {len(analyzed)} document(s): "
            f"{[d.id for d in analyzed]}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
