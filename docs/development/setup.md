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
| `make install` | `make install-backend install-frontend` | Install all dependencies |
| `make install-backend` | `pip install -r requirements.txt` | Install Python dependencies |
| `make install-frontend` | `npm install` | Install Node dependencies |
| `make check` | `make lint typecheck test` | Run all checks (mirrors CI) |
| `make lint` | `make lint-backend lint-frontend` | Lint both codebases |
| `make lint-backend` | `ruff check .` | Lint Python code |
| `make lint-frontend` | `npx eslint .` | Lint TypeScript code |
| `make typecheck` | `npx tsc --noEmit` | TypeScript type checking |
| `make test` | `pytest tests/ -v` | Run backend tests |
| `make fmt` | `ruff format . && ruff check --fix .` | Format Python code |
| `make generate-api` | `bash scripts/generate-api.sh` | Generate TypeScript types from OpenAPI spec |
| `make docs-serve` | `mkdocs serve` | Preview docs locally (port 8000) |
| `make docs-build` | `mkdocs build` | Build docs site |

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
