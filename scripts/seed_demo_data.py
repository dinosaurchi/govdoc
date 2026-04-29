#!/usr/bin/env python3
"""
Seed canonical demo scenarios from bundled hard-case PDFs.

Build the full deterministic demo state using the live provider.

This fails fast if Model Studio credentials are missing or if any seeded
scenario cannot be extracted/analyzed/staged into the expected workflow
state. Use this for operator rehearsal and local demo prep.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.core.config import settings  # noqa: E402
from app.core.config_loader import load_prompt_versions_config  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.ai.real_provider import RealAIProvider  # noqa: E402
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
        settings.validate_ai_config()
        svc = DemoService(db)
        provider = RealAIProvider()
        registry = _build_prompt_registry(db)
        docs = await svc.reset_demo_ready(provider, registry)
        print(f"seed_demo_data: staged {len(docs)} demo documents")
        for doc in docs:
            print(f"- {doc.status.value}: {doc.title} ({doc.id})")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
