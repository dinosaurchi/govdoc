# GovDoc SecureFlow

Public-sector document intake and triage system baseline.

## Project Structure (Monorepo)

- `web/`: Next.js 15 + TypeScript + Tailwind (Frontend)
- `api/`: FastAPI + Python 3.12 + SQLAlchemy (Backend)
- `deploy/`: Multi-stage Dockerfiles for web and api.
- `data/`: Persistent SQLite storage (`secureflow.db`).

## Baseline Capabilities (Pass 1.6)

- **Workflow State Machine:** 10-state administrative document lifecycle defined.
- **Service Facades:** Dedicated boundaries for AI Analysis, Text Extraction, and Vector Retrieval.
- **Role Context Switcher:** UI-driven role simulation (Clerk, Reviewer, Consultant, Supervisor) synced via `X-Role` headers.
- **Persistence:** SQLAlchemy repositories mapping to SQLite with Alembic migration history.
- **Mock-Driven Logic:** Business logic and AI services are currently mocked behind interfaces in `api/app/services/`.

## Local Development

1. **Setup Environments:**
   - Copy `.env.example` to `.env` (Frontend and Backend share this for baseline simplicity).
   - Ensure you have Python 3.12 and Node 20+ installed.

2. **Backend Commands:**
   ```bash
   make install   # Install all deps
   make migrate   # Apply Alembic migrations
   ```

3. **Combined Dev Mode:**
   ```bash
   make dev       # Starts Next.js and FastAPI (via concurrent scripts)
   ```

4. **Container Mode:**
   ```bash
   make up        # docker-compose up
   ```

## Development Status

This repository has completed **Pass 1.6: Structural Baseline Cleanup**.
- The service boundaries are strict.
- The API is repository-backed (using JSON placeholders where logic is missing).
- The database schema is fully defined and synced.
- The repository is officially ready for **Pass 2: Business Logic Implementation**.
