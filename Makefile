.PHONY: dev dev-backend dev-frontend install install-backend install-frontend generate-api lint lint-backend lint-frontend typecheck test test-backend test-frontend fmt fmt-backend fmt-check fmt-check-backend check docs-serve docs-build docker-build docker-dev docker-up docker-down docker-clean

dev:
	make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

generate-api:
	bash scripts/generate-api.sh

check: lint typecheck test fmt-check     ## Run all checks (mirrors CI)

lint: lint-backend lint-frontend
lint-backend:
	cd backend && ruff check .
lint-frontend:
	cd frontend && npx eslint .

typecheck:
	cd frontend && npx tsc --noEmit

test: test-backend test-frontend
test-backend:
	cd backend && pytest tests/ -v
test-frontend:
	cd frontend && npm test

fmt: fmt-backend
fmt-backend:
	cd backend && ruff format . && ruff check --fix .

fmt-check: fmt-check-backend
fmt-check-backend:
	cd backend && ruff format --check . && ruff check .

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build

docker-build:
	docker compose build

docker-dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

docker-up:
	docker compose up --build

docker-down:
	docker compose down

docker-clean:
	docker compose down -v
