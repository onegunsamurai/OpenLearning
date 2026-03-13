---
name: test-audit
description: Audit test coverage and quality across both stacks
---

# Test Coverage & Quality Audit

Analyze the test suite for coverage gaps, weak assertions, and missing edge cases.

## Steps

### 1. Map Source → Test Files

**Backend:**
- For each file in `backend/app/routes/`, `backend/app/agents/`, `backend/app/models/`, `backend/app/services/` — find the corresponding test file in `backend/tests/`.
- Flag any source file with no corresponding test file.

**Frontend:**
- For each file in `frontend/src/` (components, hooks, stores, lib) — find co-located `*.test.ts(x)` files.
- Flag any source file with non-trivial logic but no test file.

### 2. Assess Test Quality

For each test file, check:
- **Assertion strength:** Tests that only check `toBeTruthy()` or status codes without verifying response bodies are weak.
- **Over-mocking:** Tests with more than 3 `mock`/`vi.mock`/`patch` calls may be testing mocks, not code.
- **Edge cases:** Look for missing tests around empty inputs, error responses, boundary values.
- **Error paths:** Verify tests exist for exception/error branches, not just happy paths.
- **Async handling:** Backend tests should use `async def` + `await`; frontend tests should properly await async operations.

### 3. Run Test Suites

```bash
cd backend && pytest tests/ -v 2>&1
cd frontend && npm test 2>&1
```

Report pass/fail counts and any failures.

## Output Format

| Source File | Test File | Status | Issues |
|-------------|-----------|--------|--------|
| `routes/assess.py` | `tests/test_assess.py` | Covered | Weak assertions on line 42 |
| `agents/calibrator.py` | — | **Missing** | No test file exists |

Then provide prioritized recommendations:
1. **Critical:** Untested files with complex logic
2. **High:** Tests with weak assertions or excessive mocking
3. **Medium:** Missing edge case coverage
