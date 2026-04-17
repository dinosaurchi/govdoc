# Contributing to GovDoc SecureFlow

Thank you for your interest in contributing to GovDoc SecureFlow! We welcome contributions of all kinds — bug fixes, new features, documentation improvements, and more. This guide will help you get started quickly.

---

## Getting Started

### Prerequisites

- **Docker** & **Docker Compose** v2
- **Node.js** 20+
- **Python** 3.12+

### Setup

```bash
# 1. Clone the repository
git clone <repo-url> && cd govdoc

# 2. Configure environment
cp .env.example .env
# Edit .env with your Model Studio API key and preferences

# 3. Start all services
make up

# 4. (Optional) Seed demo data
make seed-demo
```

The frontend will be available at `http://localhost:3000` and the API docs at `http://localhost:8000/docs`.

---

## Development Workflow

1. **Create a branch** from `main` with a descriptive name (e.g., `feat/document-search`, `fix/routing-error`).
2. **Make your changes** — keep commits small and focused.
3. **Run the full CI pipeline** before committing:
   ```bash
   make ci
   ```
4. **Commit** — use the conventions described below. If your changes were AI-assisted, prefix the message with `[AI]`.
5. **Push and open a Pull Request** against `main`.

---

## Project Structure

```
govdoc/
├── web/          # React 19 + Vite 6 + TypeScript + Tailwind CSS v4 frontend
├── api/          # FastAPI + SQLAlchemy 2.x + Alembic backend
│   ├── app/      # Application code (routes, services, models, adapters)
│   ├── tests/    # Pytest suites (unit, integration, contract)
│   └── alembic/  # Database migration scripts
├── e2e/          # Playwright E2E tests
├── docs/         # Project documentation and implementation plans
├── scripts/      # Utility scripts (seeding, QA, credentials)
└── deploy/       # Dockerfiles (Dockerfile.api, Dockerfile.web)
```

Runtime data (SQLite database, uploads) lives in `data/` and is gitignored — never commit data files.

---

## Code Style

### Frontend

- **ESLint + Prettier** — enforced via `web/eslint.config.mjs`. Run `make lint` to check.
- **TypeScript strict mode** — all new code must be fully typed.
- **Functional components** with hooks for state management. Avoid class components.
- Follow existing patterns for component structure, naming, and file organization.

### Backend

- **Ruff** — configured in `api/ruff.toml` with a line length of 120. Run `make lint` to check.
- **Python type hints** — all function signatures should include type annotations.
- **Pydantic schemas** for every request and response body. Keep models in `api/app/models/` and schemas in `api/app/schemas/`.
- All API endpoints must be documented via FastAPI's OpenAPI support.

---

## Testing

All new logic must have corresponding tests. The CI pipeline enforces this.

### Frontend (Vitest)

- Test files go in `web/src/**/*.test.ts` (co-located with source).
- Run: `npm test --prefix web`

### Backend (Pytest)

- Test files go in `api/tests/`.
- Use markers to categorize tests:
  - `@pytest.mark.unit` — isolated unit tests
  - `@pytest.mark.integration` — tests that touch the database or external services
  - `@pytest.mark.contract` — API contract tests
- Run: `cd api && python -m pytest tests -q -m "unit or contract or mock_integration"`

### End-to-End (Playwright)

- Critical user flows should have E2E tests in `e2e/`.
- Requires a running stack (`make up`). Run: `make test-e2e`

### Run Everything

```bash
make test    # Frontend + backend tests
make ci      # Full pipeline: lint → build → test
```

---

## Commit Messages

- Use **imperative mood**: "Add document search" not "Added document search".
- Keep the subject line under 72 characters.
- Reference issue numbers when applicable: `"Fix routing loop (#42)"`.
- Prefix with `[AI]` for AI-assisted commits: `"[AI] Add classification endpoint"`.
- Do not add AI co-author lines or similar metadata to commit messages.

---

## Pull Request Guidelines

- **`make ci` must pass** — CI failures will block the merge.
- **Include tests** for any new feature or bug fix.
- **Update documentation** if you change behavior, add endpoints, or modify configuration.
- **Keep PRs focused** — one concern per PR makes review faster and reduces risk.
- Write a clear description explaining the **why** and **what** of your changes.

---

## Common Commands

| Command | Description |
|---------|-------------|
| `make up` | Build and start all services (Docker) |
| `make down` | Stop all services |
| `make ci` | Run full CI pipeline (lint → build → test) |
| `make test` | Run frontend + backend tests |
| `make lint` | Run ESLint and Ruff |
| `make build` | Build frontend and Docker images |
| `make migrate` | Run database migrations |
| `make seed-demo` | Seed demo documents and reference corpus |
| `make logs` | Tail service logs |
| `make shell` | Open a shell in the API container |

---

Thank you for contributing to GovDoc SecureFlow!
