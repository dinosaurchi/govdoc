.PHONY: install dev build test clean

install:
	npm install
	pip install -r api/requirements.txt

dev:
	npm run dev

migrate:
	cd api && alembic upgrade head

up:
	docker-compose up -d

down:
	docker-compose down

build:
	npm run build

test:
	npm test --prefix web
	pytest api/tests

clean:
	rm -rf web/.next api/__pycache__
