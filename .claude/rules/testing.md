# Testing Rules

## Backend (Python)

- **Runner:** pytest + pytest-asyncio
- **Config:** `pyproject.toml` — uses `asyncio_mode = "auto"` if configured, otherwise mark with `@pytest.mark.asyncio`
- **Fixtures:** Define shared fixtures in `conftest.py` at the appropriate scope
- **Organization:** Class-based grouping (`class TestAssessRoute:`) for related tests
- **Async:** Use `async def` for test functions that exercise async code paths
- **Mocking:** Mock LLM/external API calls only — test real business logic, database interactions, and Pydantic validation directly
- **HTTP testing:** Use `httpx.AsyncClient` with FastAPI's `TestClient` pattern
- **Command:** `cd backend && pytest tests/ -v`

## Frontend (TypeScript)

- **Runner:** Vitest + jsdom environment
- **Config:** `vitest.config.ts` — globals enabled (no need to import `describe`, `it`, `expect`)
- **Test files:** Co-located as `*.test.ts` or `*.test.tsx` next to source files
- **Mocking:** `vi.mock()` calls must appear before imports of the mocked module
- **Components:** Use React Testing Library (`@testing-library/react`) — query by role/text, not test IDs
- **State:** Clean up `sessionStorage` and Zustand store state between tests
- **Command:** `cd frontend && npm test` (single run) or `cd frontend && npx vitest` (watch mode)

## Philosophy

- Test real behavior, not implementation details
- Mock only at service/API boundaries — never mock internal functions for convenience
- Every bug fix must include a regression test
- Test edge cases: empty inputs, error responses, boundary values, concurrent operations
- Test error paths: network failures, invalid data, unauthorized access
- Prefer integration-style tests over isolated unit tests when they add more confidence
- If a test needs more than 3 mocks, the code under test may need refactoring
