.PHONY: install dev build test clean lint ci migrate

install:
	npm install
	pip install -r api/requirements.txt

dev:
	npm run dev

migrate:
	mkdir -p data api/data
	cd api && alembic upgrade head

up:
	docker-compose up -d

down:
	docker-compose down

build:
	npm run build

lint:
	npm run lint --prefix web
	cd api && python -m compileall -q app

test:
	mkdir -p data api/data
	cd api && alembic upgrade head && PYTHONPATH=. pytest tests -q

ci: lint build test

clean:
	rm -rf web/.next api/__pycache__
