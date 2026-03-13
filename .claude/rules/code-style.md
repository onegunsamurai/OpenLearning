# Code Style Rules

## Python (Backend)

- **Linter/Formatter:** Ruff — rules `E, W, F, I, UP, B, SIM, RUF` (ignored: `E501, B008, RUF012`)
- **Line length:** 100 characters
- **Quotes:** Double quotes (`"`)
- **Imports:** Use `from __future__ import annotations` at the top of every module
- **Import order:** isort via Ruff — stdlib → third-party → `app.*` (first-party)
- **Async:** All I/O operations must be `async` — use `async def` for route handlers and service functions
- **Models:** Use Pydantic `BaseModel` for internal models, `CamelModel` for API-facing models (camelCase serialization via `alias_generator`)
- **Naming:** `snake_case` for variables, functions, modules; `PascalCase` for classes
- **Type hints:** Required on all function signatures
- **Format on save:** `ruff format .` then `ruff check --fix .`

## TypeScript (Frontend)

- **Linter:** ESLint flat config (`eslint.config.mjs`) — extends `next/core-web-vitals` + `next/typescript`
- **Strict mode:** `"strict": true` in `tsconfig.json`
- **Import alias:** Always use `@/` prefix (maps to `./src/*`)
- **Client components:** Add `"use client"` directive at top of any file using hooks, event handlers, or browser APIs
- **Naming:** `camelCase` for variables/functions, `PascalCase` for components/types/interfaces, `kebab-case` for directories and file names
- **No Prettier:** Formatting is handled by ESLint alone
- **Format on save:** `npx eslint --fix <file>`

## General

- Run `make check` before committing — this runs lint + typecheck + test (mirrors CI)
- **Never edit** files in `frontend/src/lib/generated/` manually — these are auto-generated from OpenAPI
- **Never edit** `backend/openapi.json` manually — run `python scripts/export-openapi.py` to regenerate
- Prefer explicit code over clever abstractions
- Keep imports organized and remove unused ones
