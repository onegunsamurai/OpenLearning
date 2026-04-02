# Development Setup

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| pip | Latest | Python package manager |
| npm | Latest | Node package manager |

## Installation

```bash
git clone https://github.com/onegunsamurai/OpenLearning.git
cd OpenLearning
make install
```

## Environment Configuration

### Backend (`backend/.env`)

```bash
cp backend/.env.example backend/.env
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | No | — | Fallback Anthropic API key (users provide their own via BYOK) |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Allowed CORS origins |
| `DATABASE_URL` | No | `postgresql+asyncpg://openlearning:openlearning@localhost:5432/openlearning` | SQLAlchemy async database URL |
| `TEST_DATABASE_URL` | No | — | Database URL for tests (used by CI and `conftest.py`) |
| `LANGSMITH_API_KEY` | No | — | LangSmith API key (for tracing) |
| `LANGSMITH_PROJECT` | No | `open-learning` | LangSmith project name |
| `LANGSMITH_TRACING` | No | `false` | Enable LangSmith tracing |
| `GITHUB_CLIENT_ID` | No* | — | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | No* | — | GitHub OAuth app secret |
| `JWT_SECRET_KEY` | No* | — | JWT signing key (random 256-bit hex string) |
| `ENCRYPTION_KEY` | No* | — | Fernet key for API key encryption |
| `FRONTEND_URL` | No | `http://localhost:3000` | Frontend URL for OAuth redirects |

*Required for authentication. Without these, protected endpoints return 501/401. Demo mode works without auth.

### Frontend (`frontend/.env.local`)

```bash
cp frontend/.env.example frontend/.env.local
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend API URL |

## Running Locally

```bash
# Start both frontend and backend concurrently
make dev

# Or run them separately
make dev-backend   # http://localhost:8000
make dev-frontend  # http://localhost:3000
```

## Makefile Reference

| Target | Command | Description |
|--------|---------|-------------|
| `make dev` | `make -j2 dev-backend dev-frontend` | Start both servers concurrently |
| `make dev-db` | `docker compose -f ... up db -d` | Start PostgreSQL container (port 5432 exposed) |
| `make dev-backend` | `cd backend && uvicorn app.main:app --reload --port 8000` | Start backend with hot reload |
| `make dev-frontend` | `cd frontend && npm run dev` | Start frontend dev server |
| `make install` | `make install-backend install-frontend install-hooks` | Install all dependencies and pre-commit hooks |
| `make install-backend` | `cd backend && pip install -r requirements.txt` | Install Python dependencies |
| `make install-frontend` | `cd frontend && npm install` | Install Node dependencies |
| `make check` | `make lint typecheck test fmt-check build-frontend` | Run all checks (mirrors CI) |
| `make lint` | `make lint-backend lint-frontend` | Lint both codebases |
| `make lint-backend` | `cd backend && ruff check .` | Lint Python code |
| `make lint-frontend` | `cd frontend && npx eslint .` | Lint TypeScript code |
| `make typecheck` | `cd frontend && npx tsc --noEmit` | TypeScript type checking |
| `make test` | `make test-backend test-frontend` | Run all tests (backend + frontend) |
| `make test-backend` | `cd backend && pytest tests/ -v` | Run backend tests |
| `make test-frontend` | `cd frontend && npm test` | Run frontend tests (Vitest) |
| `make fmt` | `cd backend && ruff format . && ruff check --fix .` | Format Python code |
| `make fmt-backend` | `cd backend && ruff format . && ruff check --fix .` | Format Python code (backend only) |
| `make fmt-check` | `make fmt-check-backend` | Check Python formatting (no changes) |
| `make fmt-check-backend` | `cd backend && ruff format --check .` | Verify Python code is formatted |
| `make build-frontend` | `cd frontend && npm run build` | Build frontend for production |
| `make install-hooks` | `pip install pre-commit && pre-commit install` | Install pre-commit git hooks |
| `make pre-commit` | `pre-commit run --all-files` | Run all pre-commit checks manually (runs Ruff, `forbid-env-files.sh`, and `lint-frontend-staged.sh`) |
| `make generate-api` | `bash scripts/generate-api.sh` | Generate TypeScript types from OpenAPI spec |
| `make docs-serve` | `mkdocs serve` | Preview docs locally (port 8000 — conflicts with dev-backend; use mkdocs serve --dev-addr 127.0.0.1:8001 to run both) |
| `make docs-build` | `mkdocs build` | Build docs site |
| `make docker-build` | `docker compose build` | Build Docker images |
| `make docker-dev` | `docker compose ... up --build` | Start stack with hot-reload |
| `make docker-up` | `docker compose up --build` | Start production-like stack |
| `make docker-down` | `docker compose down` | Stop containers |
| `make docker-clean` | `docker compose down -v` | Stop and remove volumes |

### Pre-commit Hooks

`make install` sets up pre-commit hooks automatically. The hooks run on every commit and include:

- **Ruff** — Python lint and format checks
- **`scripts/forbid-env-files.sh`** — Blocks committing `.env` files with secrets
- **`scripts/lint-frontend-staged.sh`** — Lints staged frontend files with ESLint

Configuration lives in `.pre-commit-config.yaml`. Run `make pre-commit` to execute all hooks manually.

## Type Generation

TypeScript types are auto-generated from the backend's OpenAPI spec:

```bash
# With backend running
make generate-api
```

This generates types into `frontend/src/lib/generated/`. **Do not edit these files manually** — they are overwritten on each generation.

## Database

The backend requires PostgreSQL. Start a local instance with Docker:

```bash
make dev-db
```

This uses both `docker-compose.yml` and `docker-compose.dev.yml` to start a PostgreSQL container with port 5432 exposed to the host, using default credentials (`openlearning:openlearning`). Tables are created automatically on first run via `init_db()`.

To use your own PostgreSQL instance, set `DATABASE_URL` in `backend/.env`.

For tests, set `TEST_DATABASE_URL` to point to a separate database (CI uses `openlearning_test`).

## Worktree Docker Environments

When developing in a git worktree (`.claude/worktrees/issue-<N>`), use isolated Docker
environments to avoid port conflicts with other worktrees or the main repo:

```bash
make worktree-dev ISSUE=144          # start isolated stack
make worktree-dev-down ISSUE=144     # stop stack
make worktree-e2e ISSUE=144          # run E2E tests against stack
```

Each worktree gets unique ports derived from the issue number (e.g., issue 144: frontend on 3144, backend on 8144). See [Worktree Environments](worktree-dev.md) for full details.

| Target | Description |
|--------|-------------|
| `make worktree-dev ISSUE=N` | Start isolated Docker stack for worktree |
| `make worktree-dev-down ISSUE=N` | Stop the stack (add `VOLUMES=yes` to wipe DB) |
| `make worktree-e2e ISSUE=N` | Start stack + run Playwright E2E tests |
