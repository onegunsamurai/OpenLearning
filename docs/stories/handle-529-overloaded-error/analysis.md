# Story Analysis: Handle Anthropic API 529 Overloaded Error

## Issue
GitHub Issue #127 — P1 priority

## Problem Statement
When the Anthropic API returns HTTP 529 (`overloaded_error`), the backend does not
recognise this error type. The raw API error propagates to the user with no actionable
feedback and no retry logic.

## Root Cause
The `OverloadedError` class exists in `anthropic._exceptions` but is not handled in:
1. `classify_anthropic_error()` in `backend/app/services/ai.py`
2. The retry tuple in `get_structured_model()`
3. Global exception handlers in `backend/app/main.py`
4. Frontend `api-error-display.tsx` has no case for HTTP 503

## Acceptance Criteria
- [ ] Backend catches `OverloadedError` (HTTP 529) from all Anthropic API call sites
- [ ] `ainvoke_structured` retries on `OverloadedError` with exponential backoff (same as other transient errors)
- [ ] `classify_anthropic_error` maps `OverloadedError` → 503 with user-friendly message and `Retry-After` header (default 30s)
- [ ] Global exception handler registered for `OverloadedError`
- [ ] SSE streaming catches `OverloadedError` and yields `[ERROR]` event with status 503
- [ ] Frontend displays user-friendly message for 503: "The AI service is currently overloaded. Please try again in a moment."
- [ ] Frontend shows retry button for 503 with auto-retry countdown when `Retry-After` is present; manual retry only when absent
- [ ] Regression tests cover the 529 error path in:
  - Unit test for `classify_anthropic_error`
  - Integration test via gap-analysis route
  - SSE streaming test via assessment route
  - Frontend component test for 503 display

## Edge Cases
- 529 during SSE streaming mid-response (already handled by existing try/except in `_assessment_event_stream`)
- 529 after all retries exhausted (should surface 503 to user)
- Concurrent 529 from multiple users (each gets their own retry cycle)

## Non-Functional Requirements
- No new dependencies required
- Import `OverloadedError` from `anthropic._exceptions` (private but stable; used internally by SDK)
- Follow existing error handling patterns exactly

## Scope
- Backend: `ai.py`, `main.py`
- Frontend: `api-error-display.tsx`
- Tests: `test_anthropic_error_handling.py`, new frontend test
- No schema changes, no API contract changes, no database changes
