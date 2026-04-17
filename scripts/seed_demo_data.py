#!/usr/bin/env python3
"""
Load baseline roles/departments and seeded hero documents (idempotent-safe for roles/depts).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.db.session import SessionLocal  # noqa: E402
from app.services.demo import DemoService  # noqa: E402


async def main() -> None:
    db = SessionLocal()
    try:
        svc = DemoService(db)
        docs = await svc.seed_scenarios()
        print(f"seed_demo_data: created/updated seeded documents: {[d.id for d in docs]}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
