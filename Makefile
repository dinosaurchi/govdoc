.PHONY: install dev build lint test ci clean migrate up down logs qa check-credentials seed-demo up-remote remote-package test-ai test-e2e

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
	cd api && $(PY) -m alembic upgrade head && PYTHONPATH=. $(PY) -m pytest tests -q

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
	$(PY) scripts/check_credentials.py

seed-demo:
	mkdir -p data api/data
	cd api && $(PY) -m alembic upgrade head && cd .. && $(PY) scripts/seed_demo_data.py

remote-package:
	bash scripts/remote_package.sh

up-remote:
	bash scripts/remote_up.sh

test-ai:
	@echo "test-ai: not implemented — live Model Studio calls are out of scope for Pass 3 baseline" >&2
	@exit 1

test-e2e:
	@echo "test-e2e: Playwright suite not added yet; see e2e/README.md" >&2
	@exit 1
