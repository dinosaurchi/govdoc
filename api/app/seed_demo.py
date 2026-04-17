from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import settings
from app.core.config_loader import load_prompt_versions_config
from app.db.session import SessionLocal
from app.services.ai.real_provider import RealAIProvider
from app.services.demo import DemoService
from app.services.prompt_registry import PromptRegistry


def _build_prompt_registry(db) -> PromptRegistry:
    project_root = Path(__file__).resolve().parents[2]
    prompt_versions_path = project_root / "api" / "config" / "prompt_versions.yaml"
    prompts_dir = project_root / settings.PROMPT_CONFIG_PATH
    labels = load_prompt_versions_config(prompt_versions_path)
    registry = PromptRegistry(prompts_dir, db, labels)
    registry.register_all()
    return registry


async def main() -> None:
    settings.validate_ai_config()

    db = SessionLocal()
    try:
        registry = _build_prompt_registry(db)
        provider = RealAIProvider()
        svc = DemoService(db)
        docs = await svc.seed_demo_ready(provider, registry)
        summary = [{"id": doc.id, "title": doc.title, "status": doc.status.value} for doc in docs]
        print(f"seed_demo_ready: staged {len(summary)} demo documents")
        for row in summary:
            print(f"- {row['status']}: {row['title']} ({row['id']})")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
