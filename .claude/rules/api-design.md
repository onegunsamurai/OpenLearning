# API Design Rules

## REST Conventions

- All routes live under the `/api` prefix
- Use `CamelModel` (Pydantic with `alias_generator=to_camel`) for request/response models exposed to the frontend
- Set `response_model_by_alias=True` on route decorators when using aliased models
- Route files in `backend/app/routes/` — one file per resource domain

## SSE Streaming

- Content-Type: `text/event-stream`
- Use `sse-starlette` for streaming responses
- Control signals sent as SSE data:
  - `[DONE]` — stream complete
  - `[META]` — metadata payload (JSON follows)
  - `[ERROR]` — error payload (JSON follows)
- Frontend reads streams with `EventSource` or fetch + `ReadableStream`

## Error Handling

- Use `fastapi.HTTPException` with appropriate status codes:
  - `400` — bad request / validation failure
  - `404` — resource not found
  - `500` — unexpected server error
- Frontend uses an `unwrap()` helper to extract response data or throw typed errors
- Always return structured error responses, never raw strings

## OpenAPI Codegen Pipeline

The frontend API client is auto-generated from the backend's OpenAPI spec:

1. **Source of truth:** Pydantic models in `backend/app/models/`
2. **Export spec:** `python scripts/export-openapi.py` → writes `backend/openapi.json`
3. **Generate client:** `bash scripts/generate-api.sh` → generates `frontend/src/lib/generated/`
4. **Shortcut:** `make generate-api` runs the full pipeline
5. **Type re-exports:** Public types surfaced via `frontend/src/lib/types.ts`

### Workflow

- After changing any Pydantic model or route signature, run `make generate-api`
- Never edit files in `frontend/src/lib/generated/` manually
- Import generated types from `@/lib/types` (re-export barrel), not directly from `@/lib/generated/`
- Verify sync: compare route count in backend code vs `backend/openapi.json` paths
