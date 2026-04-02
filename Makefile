.PHONY: dev dev-backend dev-frontend dev-db install install-backend install-frontend install-hooks generate-api lint lint-backend lint-frontend typecheck test test-backend test-frontend test-e2e test-e2e-headed test-e2e-report fmt fmt-backend fmt-check fmt-check-backend check pre-commit build-frontend docs-serve docs-build docker-build docker-dev docker-up docker-down docker-clean worktree-create worktree-remove worktree-list worktree-dev worktree-dev-down worktree-e2e

dev:
	make -j2 dev-backend dev-frontend

dev-db:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up db -d

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

install: install-backend install-frontend install-hooks

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

install-hooks:
	pip install pre-commit
	pre-commit install

pre-commit:
	pre-commit run --all-files

generate-api:
	bash scripts/generate-api.sh

check: lint typecheck test fmt-check build-frontend     ## Run all checks (mirrors CI)

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

test-e2e:
	cd frontend && npx playwright test

test-e2e-headed:
	cd frontend && npx playwright test --headed

test-e2e-report:
	cd frontend && npx playwright show-report

fmt: fmt-backend
fmt-backend:
	cd backend && ruff format . && ruff check --fix .

fmt-check: fmt-check-backend
fmt-check-backend:
	cd backend && ruff format --check .

build-frontend:
	cd frontend && npm run build

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

# --- Worktree management (parallel Claude Code sessions) ---
worktree-create:
	@bash scripts/worktree-create.sh $(ISSUE)

worktree-remove:
	@bash scripts/worktree-remove.sh $(ISSUE)

worktree-list:
	@bash scripts/worktree-list.sh

# --- Worktree Docker environments (isolated parallel dev) ---
worktree-dev:
	@bash scripts/worktree-dev.sh $(if $(ISSUE),"$(ISSUE)") $(if $(MODE),"--mode=$(MODE)")

worktree-dev-down:
	@bash scripts/worktree-dev.sh --down $(if $(ISSUE),"$(ISSUE)") $(if $(VOLUMES),--volumes)

worktree-e2e:
	@if [ -z "$(ISSUE)" ]; then echo "Error: ISSUE is required. Usage: make worktree-e2e ISSUE=<N>" >&2; exit 1; fi; \
	  if ! echo "$(ISSUE)" | grep -qE '^#?[0-9]+$$'; then \
	    echo "Error: ISSUE must be a number (e.g. 152 or #152), got '$(ISSUE)'" >&2; exit 1; \
	  fi; \
	  ISSUE_NUM=$$(echo "$(ISSUE)" | sed -E 's/^#?([0-9]+)$$/\1/'); \
	  bash scripts/worktree-dev.sh "$$ISSUE_NUM" $(if $(MODE),"--mode=$(MODE)") && \
	  FRONTEND_PORT=$$(docker compose -p "openlearning-wt-$$ISSUE_NUM" port frontend 3000 2>/dev/null | cut -d: -f2) && \
	  BACKEND_PORT=$$(docker compose -p "openlearning-wt-$$ISSUE_NUM" port backend 8000 2>/dev/null | cut -d: -f2) && \
	  BASE_URL="http://localhost:$$FRONTEND_PORT" \
	  API_URL="http://localhost:$$BACKEND_PORT" \
	  $(MAKE) test-e2e
