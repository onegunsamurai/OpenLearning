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
| `ANTHROPIC_API_KEY` | Yes | — | Your Anthropic API key |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Allowed CORS origins |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./data/openlearning.db` | SQLAlchemy async database URL |
| `LANGSMITH_API_KEY` | No | — | LangSmith API key (for tracing) |
| `LANGSMITH_PROJECT` | No | `open-learning` | LangSmith project name |
| `LANGSMITH_TRACING` | No | `false` | Enable LangSmith tracing |

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
| `make dev-backend` | `uvicorn app.main:app --reload --port 8000` | Start backend with hot reload |
| `make dev-frontend` | `npm run dev` | Start frontend dev server |
| `make install` | `make install-backend install-frontend install-hooks` | Install all dependencies and pre-commit hooks |
| `make install-backend` | `pip install -r requirements.txt` | Install Python dependencies |
| `make install-frontend` | `npm install` | Install Node dependencies |
| `make check` | `make lint typecheck test fmt-check build-frontend` | Run all checks (mirrors CI) |
| `make lint` | `make lint-backend lint-frontend` | Lint both codebases |
| `make lint-backend` | `ruff check .` | Lint Python code |
| `make lint-frontend` | `npx eslint .` | Lint TypeScript code |
| `make typecheck` | `npx tsc --noEmit` | TypeScript type checking |
| `make test` | `make test-backend test-frontend` | Run all tests (backend + frontend) |
| `make test-backend` | `pytest tests/ -v` | Run backend tests |
| `make test-frontend` | `npm test` | Run frontend tests (Vitest) |
| `make fmt` | `cd backend && ruff format . && ruff check --fix .` | Format Python code |
| `make fmt-backend` | `cd backend && ruff format . && ruff check --fix .` | Format Python code (backend only) |
| `make fmt-check` | `make fmt-check-backend` | Check Python formatting (no changes) |
| `make fmt-check-backend` | `cd backend && ruff format --check .` | Verify Python code is formatted |
| `make build-frontend` | `npm run build` | Build frontend for production |
| `make install-hooks` | `pip install pre-commit && pre-commit install` | Install pre-commit git hooks |
| `make pre-commit` | `pre-commit run --all-files` | Run all pre-commit checks manually (runs Ruff, `forbid-env-files.sh`, and `lint-frontend-staged.sh`) |
| `make generate-api` | `bash scripts/generate-api.sh` | Generate TypeScript types from OpenAPI spec |
| `make docs-serve` | `mkdocs serve` | Preview docs locally (port 8000) |
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

SQLite databases are created automatically on first run:

- `data/openlearning.db` — Assessment sessions and results
- `data/checkpoints.db` — LangGraph pipeline checkpoints

Both are gitignored. Delete them to start fresh.
