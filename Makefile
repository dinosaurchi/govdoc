.PHONY: install dev build test clean lint ci migrate

PY := .venv/bin/python

install:
	npm install
	pip install -r api/requirements.txt

dev:
	npm run dev

migrate:
	mkdir -p data api/data
	cd api && ../$(PY) -m alembic upgrade head

up:
	mkdir -p data api/data
	docker compose up -d --build

down:
	docker compose down

build:
	npm run build

lint:
	npm run lint --prefix web
	$(PY) -m compileall -q api/app

test:
	mkdir -p data api/data
	cd api && ../$(PY) -m alembic upgrade head && PYTHONPATH=. ../$(PY) -m pytest tests -q

ci: lint build test

clean:
	rm -rf web/.next api/__pycache__
