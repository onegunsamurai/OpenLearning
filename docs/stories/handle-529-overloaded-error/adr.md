# ADR: Handle Anthropic API 529 OverloadedError

## Status
Accepted

## Context
Anthropic returns HTTP 529 with `overloaded_error` when their service is under load.
The SDK raises `OverloadedError` (from `anthropic._exceptions`) for this status code.
Our error handling covers 5 other Anthropic error types but misses this one, causing
raw API errors to surface to users.

## Decision

### HTTP Status Mapping
Map `OverloadedError` to **HTTP 503 Service Unavailable**.
- 503 semantically means "server temporarily unable to handle request due to overload"
- 429 would conflate capacity overload with per-user rate limiting
- 502 would conflate upstream failure with upstream overload

### Import Strategy
Import `OverloadedError` from `anthropic._exceptions`. While this is a private module,
the class is stable (used internally by the SDK for all 529 responses) and is the only
way to add it to langchain's `retry_if_exception_type` tuple.

### Retry Behavior
Add `OverloadedError` to the retry tuple in `get_structured_model()`. This is a transient
error that should be retried with exponential backoff (same as `InternalServerError`).

### No Retry-After Header
Anthropic does not send `Retry-After` on 529 responses. We will not fabricate one.
The frontend shows a manual retry button without auto-retry countdown.

## Consequences
- Users see "The AI service is currently overloaded" instead of raw API errors
- Transient overload is retried automatically (up to 3 attempts)
- Frontend retry button available after retries exhausted
- If Anthropic adds a top-level `OverloadedError` export in a future SDK version,
  we can simplify the import
