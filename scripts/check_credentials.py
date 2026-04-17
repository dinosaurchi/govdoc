#!/usr/bin/env python3
"""
Validate Model Studio-related environment variables and run the isolated credential probe.

Pass 3 baseline: env validation is real; live Model Studio HTTP probe is explicitly
not implemented (see api/app/adapters/modelstudio/credentials.py).
Exit code 1 on any failure — never reports success for unfinished probes.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Repo root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

from app.adapters.modelstudio.credentials import (  # noqa: E402
    LiveCredentialProbeNotImplementedError,
    probe_live_credentials,
    validate_probe_env,
)


def main() -> int:
    env_file = ROOT / ".env"
    if env_file.is_file():
        # Minimal dotenv parse (no python-dotenv dependency): KEY=VALUE lines
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v

    result = validate_probe_env()
    def err(*args: object) -> None:
        print(*args, file=sys.stderr)

    if result.missing:
        err(
            "check-credentials: missing or empty required environment variables:",
            ", ".join(result.missing),
        )
        err("See .env.example for the full contract. No live probe was attempted.")
        return 1

    err("check-credentials: required env keys for Model Studio probe are present.")

    try:
        probe_live_credentials()
    except LiveCredentialProbeNotImplementedError as exc:
        err(f"check-credentials: {exc}")
        return 1
    except Exception as exc:  # pragma: no cover — defensive
        err(f"check-credentials: unexpected error: {exc}")
        return 1

    err("check-credentials: live probe reported success (unexpected in Pass 3).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
