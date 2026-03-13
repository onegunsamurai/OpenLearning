---
name: code-review
description: Pre-commit code review with structured findings
---

# Code Review

Review staged or recent changes for correctness, security, performance, and style compliance.

## Steps

### 1. Gather Changes

```bash
# Staged changes (pre-commit)
git diff --cached --name-only
git diff --cached

# Or recent changes on branch
git diff main...HEAD --name-only
git diff main...HEAD
```

Categorize files by stack: **backend** (`.py`), **frontend** (`.ts`, `.tsx`), **config/other**.

### 2. Review Checklist

**Correctness:**
- Logic errors, off-by-one, null/undefined handling
- Missing `await` on async calls
- Incorrect type annotations or missing type narrowing

**Security:**
- SQL injection, command injection, XSS vectors
- Secrets or credentials in code
- Missing input validation at API boundaries

**Performance:**
- N+1 queries or unnecessary database calls
- Large objects held in memory unnecessarily
- Missing pagination on list endpoints

**Error handling:**
- Uncaught exceptions in async code
- Missing error responses for failure paths
- Swallowed errors (empty `except:` / `.catch(() => {})`)

**Style compliance:**
- Python: Ruff rules (E/W/F/I/UP/B/SIM/RUF), async patterns, Pydantic models
- TypeScript: strict mode, `@/` imports, `"use client"` where needed
- General: DRY violations, dead code, unclear naming

**Tests:**
- Do behavioral changes have corresponding test updates?
- Are new edge cases covered?

### 3. Verify

```bash
make check
```

Report any lint, typecheck, or test failures.

## Output Format

For each finding:
- **Severity:** Critical / High / Medium / Low
- **File:Line:** exact location
- **Problem:** what's wrong
- **Fix:** suggested correction
- **Impact:** what could go wrong if not fixed
