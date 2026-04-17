.PHONY: install dev build lint test ci clean migrate up down logs qa check-credentials seed-demo up-remote remote-package test-ai test-e2e eval-ai qa-local

# Prefer project venv when present (absolute path so `cd api && …` still works)
PY := $(shell test -x "$(CURDIR)/.venv/bin/python" && echo "$(CURDIR)/.venv/bin/python" || command -v python3)

install:
	npm install
	cd api && $(PY) -m pip install -r requirements.txt

dev:
	npm run dev

migrate:
	mkdir -p data api/data
	cd api && $(PY) -m alembic upgrade head

build:
	npm run build
	docker compose build

test:
	mkdir -p data api/data
	cd api && $(PY) -m alembic upgrade head && PYTHONPATH=. $(PY) -m pytest tests -q -m "unit or contract or mock_integration" --tb=short

lint:
	npm run lint --prefix web
	cd api && $(PY) -m ruff check app/adapters tests
	$(PY) -m compileall -q api/app

ci: lint build test

clean:
	rm -rf web/dist web/node_modules/.vite api/__pycache__

up:
	mkdir -p data api/data
	docker compose up -d --build
	bash scripts/wait_for_compose_healthy.sh

down:
	docker compose down

logs:
	docker compose logs -f

APP_PORT ?= 8000
WEB_PORT ?= 3000

qa:
	$(eval _QA_HOST := $(shell docker network inspect govdoc_default --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null | head -1 || echo 127.0.0.1))
	API_URL="http://$(_QA_HOST):$(APP_PORT)" WEB_URL="http://$(_QA_HOST):$(WEB_PORT)" bash scripts/qa_local.sh

check-credentials:
	cd api && $(PY) -m pytest tests -q -m "creds" --creds --tb=short

seed-demo:
	mkdir -p data api/data
	cd api && $(PY) -m alembic upgrade head && cd .. && $(PY) scripts/seed_demo_data.py

remote-package:
	bash scripts/remote_package.sh

up-remote:
	bash scripts/remote_up.sh

test-ai:
	cd api && $(PY) -m pytest tests -q -m "live or live_integration" --live --integration --tb=short

test-e2e:
	@echo "Checking if stack is running..."
	@curl -sf http://localhost:${APP_PORT:-8000}/healthz > /dev/null 2>&1 || { echo "Error: API not running at localhost:${APP_PORT:-8000}" >&2; exit 1; }
	@curl -sf http://localhost:${WEB_PORT:-3000}/ > /dev/null 2>&1 || { echo "Error: Web not running at localhost:${WEB_PORT:-3000}" >&2; exit 1; }
	@echo "Stack is running. Running Playwright E2E tests..."
	@cd e2e && npx playwright test || { echo "E2E tests not configured yet. See e2e/README.md" >&2; exit 1; }

eval-ai:
	$(PY) scripts/eval_ai_quality.py

qa-local:
	API_URL="http://localhost:${APP_PORT:-8000}" WEB_URL="http://localhost:${WEB_PORT:-3000}" bash scripts/qa_local.sh
