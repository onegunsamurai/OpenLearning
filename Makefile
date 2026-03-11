.PHONY: dev dev-backend dev-frontend install install-backend install-frontend generate-api lint lint-backend lint-frontend typecheck test test-backend fmt fmt-backend check docs-serve docs-build

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

check: lint typecheck test          ## Run all checks (mirrors CI)

lint: lint-backend lint-frontend
lint-backend:
	cd backend && ruff check .
lint-frontend:
	cd frontend && npx eslint .

typecheck:
	cd frontend && npx tsc --noEmit

test: test-backend
test-backend:
	cd backend && pytest tests/ -v

fmt: fmt-backend
fmt-backend:
	cd backend && ruff format . && ruff check --fix .

docs-serve:
	mkdocs serve

docs-build:
	mkdocs build
