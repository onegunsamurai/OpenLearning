Run full CI checks and summarize results.

## Instructions

1. Run `make check` and capture the full output.

2. Parse the output and summarize pass/fail by category:
   - **Lint (backend):** Ruff format + Ruff check
   - **Lint (frontend):** ESLint
   - **Typecheck (frontend):** TypeScript `tsc --noEmit`
   - **Tests (backend):** pytest
   - **Tests (frontend):** Vitest
   - **Build (frontend):** Next.js build

3. For any failures:
   - Extract the specific error messages
   - Include `file:line` references
   - Suggest a fix for each failure

4. End with a clear verdict: all checks pass, or list what needs fixing before commit.
