# OpenLearning

AI-powered adaptive learning platform that identifies skill gaps and generates personalized learning plans using LangGraph-powered assessment.

## Tech Stack
- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy (async) / PostgreSQL 16
- **AI:** Anthropic Claude SDK / LangChain / LangGraph (stateful agent pipeline)
- **Frontend:** Next.js 16 (App Router) / React 19 / TypeScript 5 (strict) / Tailwind 4 / Zustand
- **Codegen:** Pydantic models -> OpenAPI spec -> generated TypeScript client

## Key Commands
- `make dev` — Run backend + frontend concurrently
- `make check` — Lint + typecheck + test + build (mirrors CI, run before committing)
- `make generate-api` — Regenerate TypeScript API client from backend OpenAPI spec
- `make fmt` — Auto-format backend code with Ruff

## Architecture
- `backend/app/routes/` — FastAPI routers (one per domain: assessment, auth, skills, etc.)
- `backend/app/agents/` — LLM agents (calibrator, evaluator, gap_analyzer, plan_generator, etc.)
- `backend/app/graph/` — LangGraph state machine (pipeline.py, router.py, state.py)
- `backend/app/models/` — Pydantic models (source of truth for OpenAPI)
- `frontend/src/app/` — Next.js pages (App Router)
- `frontend/src/components/` — React components (ui/, assessment/, onboarding/, etc.)
- `frontend/src/lib/` — Store (Zustand), generated API client, types, utils

## Critical Conventions
- Never edit `frontend/src/lib/generated/` or `backend/openapi.json` — run `make generate-api`
- After Pydantic model changes: always run `make generate-api`
- `CamelModel` for API-facing models, `BaseModel` for internal models
- `from __future__ import annotations` at top of every Python module
- Import generated types from `@/lib/types`, not `@/lib/generated/`

## Engineering Preferences
- DRY is important — flag repetition aggressively
- Well-tested code is non-negotiable
- "Engineered enough" — not fragile, not over-abstracted
- Handle more edge cases, not fewer; thoughtfulness > speed
- Explicit over clever
