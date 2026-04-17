# GovDoc SecureFlow

Public-sector **incoming document intake and triage** baseline (GovDoc SecureFlow). This repo is a real Next.js + FastAPI + SQLite application with **mocked AI/extraction/retrieval** behind isolated service interfaces.

## Pass status

**Pass 3 (current):** developer workflow, Docker health checks, QA/credential/remote scaffolds, and test layout are hardened. **Live Model Studio**, **real OCR**, and **real embeddings** are still intentionally **not** implemented.

## Repository layout

| Path | Role |
|------|------|
| `web/` | Next.js 15 (App Router) + TypeScript + Tailwind |
| `api/` | FastAPI + SQLAlchemy + Alembic |
| `deploy/` | Dockerfiles for `web` and `api` |
| `scripts/` | `check_credentials`, `seed_demo_data`, `qa_local`, `remote_*`, compose health wait |
| `data/` | SQLite DB, uploads, **gitignored** — create via compose or migrate |
| `e2e/` | Playwright placeholder only (see `e2e/README.md`) |

## Prerequisites

- Node 20+ and npm
- Python 3.12 (recommended: `python3.12 -m venv .venv`)
- Docker + Docker Compose v2 (for `make up`)

## Local development (without Docker)

1. Copy environment contract: `cp .env.example .env` and adjust if needed.
2. Install dependencies: `make install`
3. Apply migrations: `make migrate`
4. Run API + web together: `npm run dev` (from repo root; uses `concurrently`)

API defaults to port **8000**, web to **3000**. The Next app rewrites `/api/*` to the FastAPI backend (`web/next.config.ts`).

## Local development (Docker)

```bash
make up    # builds, starts api + web, waits until both healthchecks pass
make logs  # follow logs
make down  # stop stack
```

- **API liveness:** `GET /health`
- **API readiness (DB):** `GET /health/ready` — used by Docker healthchecks so the stack does not report “healthy” if SQLite is not reachable.

## Makefile targets

| Target | Purpose |
|--------|---------|
| `make install` | npm install + pip install `api/requirements.txt` |
| `make migrate` | Alembic upgrade |
| `make lint` | ESLint (web); Ruff on `api/app/adapters` + `api/tests`; `compileall` on all of `api/app` |
| `make build` | `npm run build` + `docker compose build` |
| `make test` | migrate + pytest (`api/tests`: unit + integration) |
| `make ci` | `lint` → `build` → `test` |
| `make up` / `make down` / `make logs` | Docker Compose |
| `make qa` | HTTP smoke checks (`scripts/qa_local.sh`; requires stack running) |
| `make check-credentials` | Validates Model Studio–related env vars, then **fails** until live probe exists (see below) |
| `make seed-demo` | Runs `DemoService.seed_scenarios()` (adds demo rows; repeated runs add more documents) |
| `make remote-package` | `docker compose build` + `docker save` + `deploy/bundle/` manifest (**exits 0**) |
| `make up-remote` | Runs `remote-package`, then **exits non-zero** — remote ssh/rsync apply is TODO |
| `make test-ai` | **Fails** — reserved for live Model Studio tests |
| `make test-e2e` | **Fails** — reserved for Playwright |

## Environment variables

See **`.env.example`** for the full contract. Highlights:

- **Database / CORS / storage:** `DATABASE_URL`, `ALLOWED_ORIGINS`, `LOCAL_FILE_STORAGE_ROOT`
- **Demo toggles:** `ENABLE_DEMO_MODE`, `ENABLE_CACHED_AI_RESULTS`, etc. (baseline behavior is still mock-driven)
- **Model Studio (for future live AI):** `MODELSTUDIO_API_KEY`, `MODELSTUDIO_BASE_URL`, model name variables — required for **`make check-credentials`** env validation once you fill them
- **Remote packaging contract:** `REMOTE_HOST`, `REMOTE_USER`, `REMOTE_APP_DIR` — required for `make up-remote` (see `scripts/remote_up.sh`)

## Demo data and scenarios

- On API startup, `DemoService.seed_baseline()` ensures roles and departments exist.
- **`make seed-demo`** loads additional hero/edge-case documents via `seed_scenarios()` (see `api/app/services/demo.py`).
- Re-running **`make seed-demo`** creates **additional** seeded rows (not idempotent for documents).

## What is real vs mocked (Pass 3)

| Area | Status |
|------|--------|
| UI, routing, role switcher, persistence, uploads, workflow storage | **Real** (baseline) |
| AI analysis, extraction text, retrieval hits, consultation auto-replies | **Mock** modules (`api/app/services/ai`, `extraction`, `retrieval`, …) |
| Model Studio HTTP client / OCR / embeddings | **Not implemented** — adapter stubs live under `api/app/adapters/modelstudio/` |

## What later coding agents should replace

- `api/app/services/ai/mock_provider.py` → real Model Studio adapter implementing `AIProviderInterface`
- `api/app/services/extraction/mock_provider.py` → deterministic PDF/DOCX + optional OCR path
- `api/app/services/retrieval/mock_provider.py` → embeddings + rerank as per implementation plan
- `api/app/adapters/modelstudio/credentials.py` → real `probe_live_credentials()` (generation, embed, OCR smoke)
- `scripts/remote_apply.sh` (future) → load images on VPS, `docker compose up`, remote health checks

## QA and credentials

- **`make qa`** calls `curl` against `/health`, `/health/ready`, and the web home page. It does **not** assume success if HTTP status codes are wrong.
- **`make check-credentials`** loads `.env` if present, verifies required keys for a future live probe, then **exits with failure** with an explicit *not implemented yet* message for the HTTP probe (no fake success).

## License / data

All persistent data stays under **`data/`** (gitignored). Do not commit customer or real secrets.
