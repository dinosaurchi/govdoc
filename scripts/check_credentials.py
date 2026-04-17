#!/usr/bin/env python3
"""Credential check script for Model Studio."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Repo root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))


def main() -> int:
    # Load .env if present
    import os

    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

    from app.adapters.modelstudio.credentials import probe_live_credentials

    results = probe_live_credentials()

    print("Model Studio Credential Check Results:")
    print("-" * 60)
    all_pass = True
    for key, value in results.items():
        status = "✓ PASS" if value is True else f"✗ {value}"
        print(f"  {key}: {status}")
        if value is not True:
            all_pass = False
    print("-" * 60)

    if all_pass:
        print("All checks passed!")
        return 0
    else:
        print("Some checks failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
