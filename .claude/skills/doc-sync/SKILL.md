---
name: doc-sync
description: Verify documentation accuracy against the current codebase
---

# Documentation Sync Verification

Audit project documentation to ensure it accurately reflects the current codebase.

## Mapping: Code → Docs

| Code Area | Documentation File |
|-----------|-------------------|
| `backend/app/routes/` | `docs/guides/api-reference.md` |
| `backend/app/agents/` | `docs/architecture/assessment-pipeline.md` |
| `backend/app/models/` | `docs/architecture/data-models.md` |
| `frontend/src/` | `docs/guides/knowledge-base.md` |
| `Makefile`, `scripts/` | `docs/development/` |
| System overview | `docs/architecture/overview.md` |

## Steps

1. **Inventory routes:** List all `@router` endpoints in `backend/app/routes/` and compare against `docs/guides/api-reference.md`. Flag any missing or outdated entries.

2. **Inventory agents:** List all agent classes in `backend/app/agents/` and compare against `docs/architecture/assessment-pipeline.md`. Verify the pipeline description matches the current agent graph.

3. **Check data models:** List all Pydantic models in `backend/app/models/` and compare field names/types against `docs/architecture/data-models.md`.

4. **Check commands:** Verify all `make` targets and `scripts/` referenced in docs exist and have correct syntax.

5. **Check code examples:** For any code snippets in docs, verify they compile/run against the current codebase.

6. **Validate build:** Run `mkdocs build --strict` to catch broken links and missing pages.

## Output Format

For each discrepancy found:
- **File:** doc file path and line number
- **Issue:** what's wrong (missing, outdated, incorrect)
- **Fix:** suggested correction with code reference
