---
name: auto-fix
description: >
  Automated end-to-end bug-fix pipeline. Trigger when the user says `/auto-fix`,
  `/auto-fix #N`, "fix a bug end-to-end", "find and fix an open issue",
  "auto-fix the highest priority bug", or requests an automated PR workflow
  for a GitHub issue. Also trigger on "run the fix pipeline" or
  "pick up a bug and open a PR". Do NOT trigger for manual code edits,
  one-off test runs, or partial workflows (e.g., "just open a PR").
---

# Auto-Fix Pipeline

Full automated pipeline: GitHub issue → code fix → validation → E2E → commit (with approval) → PR → CI → Copilot review → implement fixes.

**Usage:** `/auto-fix` (picks highest-priority open bug) or `/auto-fix #N` (targets specific issue)

---

## Common Commands (referenced by label throughout)

| Label | Command |
|-------|---------|
| `DIFF_FILES` | `git diff main...HEAD --name-only` |
| `DIFF_FULL` | `git diff main...HEAD` |
| `BRANCH_NAME` | `git branch --show-current` |

---

## Pipeline Rules

1. **No stage may be skipped.** Work through every stage in sequence.
2. After completing each stage, output a checkpoint:
   ```
   ✓ Stage N complete: <one-line summary>
   → Next: Stage N+1 — <stage name>
   ```
3. If a stage HALTs, follow the **Halt Cleanup** procedure at the bottom of this document.

---

## Stage 1 — Discover Bug

**If a specific issue number `#N` was given:**
```bash
gh issue view N --json number,title,body,labels,comments
```

**Otherwise, find the highest-priority open bug:**
```bash
gh issue list --label bug --state open \
  --json number,title,body,labels \
  --limit 20
```

Pick the issue with the highest priority label: **P0 > P1 > P2 > unlabeled**. If tied, pick the oldest (lowest number).

Display: `→ Targeting issue #N: <title>`

Read all comments for extra context:
```bash
gh issue view N --json comments --jq '.comments[].body'
```

---

## Stage 2 — Create Branch

**Guard: clean working tree**
```bash
git status --porcelain
```
If output is non-empty → **HALT**: "Working tree is dirty. Commit or stash your changes before running `/auto-fix`."

**Create branch:**
- Slugify the issue title: lowercase, replace spaces and special chars with hyphens, collapse consecutive hyphens, trim to 40 chars
- `git checkout -b fix/issue-NNN-<slug>`

Example: Issue #42 "Fix null pointer in assessment loader" → `fix/issue-42-fix-null-pointer-in-assessment`

---

## Stage 3 — Analyze & Fix

**Max 3 search-and-read cycles.** If you cannot identify a clear root cause after 3 cycles of searching the codebase and reading files, **HALT**: "Unable to identify root cause after 3 investigation cycles. Here is what was examined: <summary of files read, searches performed, and hypotheses considered>. Manual investigation required."

1. Cross-reference the issue description with the codebase to identify affected files:
   - Search for relevant function/class/route names mentioned in the issue
   - Check recent commits touching related areas: `git log --oneline -20 -- <path>`
   - Read the affected files fully before making any edits

2. Implement the fix:
   - Fix the root cause, not just the symptom
   - Follow code style rules (Ruff for Python, ESLint/TypeScript strict for frontend)
   - Use `async def` for all I/O operations in Python
   - Use parameterized queries via SQLAlchemy ORM — never raw SQL strings

3. Add or update tests:
   - Every bug fix must include a regression test
   - Backend: `pytest` class-based in `backend/tests/`, use real DB, mock only external APIs
   - Frontend: Vitest co-located `*.test.tsx`, query by role/text (React Testing Library)
   - Test the failure case that the issue describes, not just the happy path

---

## Stage 4 — Validation Loop

Repeat until all checks pass, **max 3 attempts**. After 3 failures → **HALT** with full diagnostic output.

### 4a. Full CI check
```bash
make check
```
If failing: read the exact error, fix it, then retry. Do not retry without understanding and fixing the cause.

### 4b. Code Review

Run `DIFF_FILES` and `DIFF_FULL`.

Review for:
- **Correctness:** logic errors, missing `await`, incorrect types, null handling
- **Security:** SQL injection, command injection, secrets in code, missing input validation
- **Performance:** N+1 queries, missing pagination, large in-memory objects
- **Error handling:** uncaught async exceptions, empty `except:` / `.catch(() => {})`, missing 4xx/5xx responses
- **Style:** Ruff rules, TypeScript strict mode, `@/` imports, `"use client"` where needed
- **Tests:** behavioral changes covered, edge cases present

Auto-fix any findings before continuing.

### 4c. API Sync

**Only run if** any of these changed: `backend/app/routes/`, `backend/app/models/`, `backend/openapi.json`, `frontend/src/lib/generated/`

```bash
grep -rn '@router\.' backend/app/routes/ --include='*.py'
```

Compare routes against `backend/openapi.json`. If stale:
```bash
make generate-api
cd frontend && npx tsc --noEmit
```

Verify `frontend/src/lib/types.ts` re-exports all types used by components.

### 4d. Doc Sync

**Only run if** any of these changed: `backend/app/routes/`, `backend/app/agents/`, `backend/app/models/`, `Makefile`, `scripts/`

Check code→docs mapping:
- Routes → `docs/guides/api-reference.md`
- Agents → `docs/architecture/assessment-pipeline.md`
- Models → `docs/architecture/data-models.md`
- Make/scripts → `docs/development/`

```bash
mkdocs build --strict
```

Fix any broken links or outdated entries.

---

## Stage 5 — E2E Test Loop

**Max 3 iterations.** If still failing after 3 → report remaining failures but continue to Stage 6.

### 5a. Precondition check
```bash
curl -s --max-time 3 http://localhost:3000 > /dev/null 2>&1
```
If this fails → **HALT**: "Dev server is not running. Start it first: `make dev`"

### 5b. Discover pages in scope

**Dynamic route discovery** — always run this first:
```bash
find frontend/src/app -name "page.tsx" | sed 's|frontend/src/app||;s|/page.tsx||;s|^$|/|'
```

Then run `DIFF_FILES` and map changed files to pages using **both** the dynamic list above and this backend→frontend mapping table:

| Changed File Pattern | URL to Test |
|---------------------|-------------|
| `frontend/src/app/<path>/**` | `/<path>` (from dynamic discovery) |
| `frontend/src/components/**` | All pages importing the component |
| `backend/app/routes/**` | Frontend pages that call those routes |

> **Maintenance note:** if you add new routes to the project, they will be picked up automatically by the `find` command above. The backend mapping row requires manual judgment.

### 5c. Run E2E tests

**Auth-required pages** (`/dashboard`, `/assess`, `/gap-analysis`, `/learning-plan`, `/export/[id]`): log in first via `http://localhost:3000/login` using credentials from env vars `$E2E_TEST_EMAIL` / `$E2E_TEST_PASSWORD`. Register if first run.

**For each page in scope:**
1. `mcp__playwright__browser_navigate` to `http://localhost:3000/<path>`
2. `mcp__playwright__browser_wait_for` for key elements
3. `mcp__playwright__browser_snapshot` — verify expected elements present
4. `mcp__playwright__browser_console_messages` — flag any `error` level messages
5. `mcp__playwright__browser_network_requests` — flag 4xx/5xx responses
6. `mcp__playwright__browser_take_screenshot` — save to `e2e-screenshots/auto-fix-NNN-<page>.png`
7. Interact with feature-specific elements and verify post-interaction state

`mcp__playwright__browser_close` after all pages tested.

**If failures found:** diagnose the root cause, fix the code, return to Stage 4.

---

## Stage 6 — Review & Commit (**PAUSE FOR APPROVAL**)

### 6a. Final review

Run `DIFF_FULL`.

Review for: code style, API design, security, testing, DRY violations. Output structured findings:
```
[SEVERITY] file_path:line_number
Problem: <description>
Fix: <suggested change>
```

Auto-fix any Critical or High findings before staging.

### 6b. Stage changes

Run `DIFF_FILES`. Stage specific files only — never `git add -A`:
```bash
git add backend/... frontend/... # list each file explicitly
```

### 6c. Draft commit message
- Format: `fix: <why, not what>` (under 72 chars)
- Good: `fix: prevent null dereference when assessment data is missing`
- Bad: `fix: update assessment_loader.py`

### 6d. PAUSE — present to user:
```
─────────────────────────────────────
READY TO COMMIT

Issue: #N — <title>
Branch: fix/issue-NNN-<slug>

Review findings: <N critical, N high, N medium, N low>

Proposed commit message:
  fix: <message>

Staged files:
  <list>
─────────────────────────────────────
Approve this commit message, or provide an alternative.
```

Wait for user approval. After approval, commit:
```bash
git commit -m "fix: "
```

---

## Stage 7 — Push & Open PR

```bash
git push -u origin fix/issue-NNN-
```

Read `.github/PULL_REQUEST_TEMPLATE.md` and fill it in. Then:
```bash
gh pr create \
  --title "fix: " \
  --body "$(cat <
-

## Test plan
- [ ] `make check` passes (lint + typecheck + test + build)
- [ ] E2E:  pass
- [ ] Regression test added in

## Related
Closes #N

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Save the PR number from the output. Display PR URL to user.

---

## Stage 8 — Wait for CI

```bash
gh pr checks  --watch
```

This blocks until all checks complete. When done:

**If all green:** continue to Stage 9.

**If any check fails (max 2 fix attempts):**
1. Get the failing run ID:
   ```bash
   gh run list --branch fix/issue-NNN-<slug> --json databaseId,status,conclusion,name \
     --jq '.[] | select(.conclusion=="failure")'
   ```
2. Read failing logs:
   ```bash
   gh run view <run-id> --log-failed
   ```
3. Diagnose root cause from logs. Fix the code.
4. Commit with a message that describes the actual failure cause (e.g., `fix: add missing await in assessment route (CI typecheck failure)`). Never use generic messages like "fix CI".
   ```bash
   git add <specific files>
   git commit -m "fix: <describe actual failure cause>"
   git push
   ```
5. Return to `gh pr checks --watch`.

After 2 failed CI fix attempts → **HALT**: "CI is still failing after 2 fix attempts. Manual investigation required." Output the full failing log.

---

## Stage 9 — Request Copilot Review

Get repo coordinates:
```bash
gh repo view --json owner,name --jq '"\(.owner.login)/\(.name)"'
```

Request Copilot as reviewer:
```bash
gh api repos/{owner}/{repo}/pulls/{PR-number}/requested_reviewers \
  -X POST \
  -f "reviewers[]=copilot-pull-request-reviewer[bot]"
```

**If this returns a 422 error:** HALT with message: "Copilot code review is not enabled on this repo. Go to: Settings → Copilot → Code review → Enable for this repo."

**Poll for review — run the query, then `sleep 30`, then re-run. Repeat up to 20 times (10 minutes total). Count iterations explicitly:**
```bash
gh api repos/{owner}/{repo}/pulls/{PR-number}/reviews \
  --jq '.[] | select(.user.login=="copilot-pull-request-reviewer[bot]") | {state, body, submittedAt}'
```

Wait until a review with state `COMMENTED` or `APPROVED` appears. If 20 iterations pass with no review → display message and ask user whether to wait longer or skip to Stage 10 with no comments.

---

## Stage 10 — Implement Copilot Fixes

**If state is `APPROVED` and no actionable comments:** Pipeline complete. Go to final output.

**If state is `COMMENTED`:**

Read the review body:
```bash
gh api repos/{owner}/{repo}/pulls/{PR-number}/reviews \
  --jq '.[] | select(.user.login=="copilot-pull-request-reviewer[bot]") | .body'
```

Read inline comments:
```bash
gh api repos/{owner}/{repo}/pulls/{PR-number}/comments \
  --jq '.[] | select(.user.login=="copilot-pull-request-reviewer[bot]") | {path, line, body}'
```

For each comment:
1. Read the referenced file at the specified line
2. Understand the suggestion in full context
3. Implement the fix (don't blindly apply — reason about correctness first)
4. If a suggestion is wrong or would break something, note it but skip it

Stage and commit:
```bash
git add
git commit -m "fix: address Copilot review feedback — "
git push
```

Return to **Stage 8** (CI wait).

**After CI passes, re-request Copilot review (repeat Stage 9).** If the second review is `APPROVED` or `COMMENTED` with no new actionable items, proceed to final output. **Max 2 review cycles** — after 2 rounds, proceed to final output regardless and note any unresolved comments.

---

## Final Output

```
─────────────────────────────────────
AUTO-FIX COMPLETE

Issue:   #N — <title>
Branch:  fix/issue-NNN-<slug>
PR:      <URL>
CI:      All checks green
Review:  Copilot approved / Copilot comments addressed (N rounds)

Stages completed:
  ✓ Bug discovered and analyzed
  ✓ Fix implemented with regression test
  ✓ make check passed
  ✓ Code review clean
  ✓ API sync verified (or: N/A)
  ✓ Doc sync verified (or: N/A)
  ✓ E2E tests passed on: <pages>
  ✓ Committed and pushed
  ✓ CI passed
  ✓ Copilot review addressed
─────────────────────────────────────
```

---

## Halt Conditions Reference

| Condition | Message |
|-----------|---------|
| Dirty working tree | "Working tree is dirty. Commit or stash your changes before running `/auto-fix`." |
| Unable to identify root cause after 3 investigation cycles | "Unable to identify root cause after 3 investigation cycles. Here is what was examined: <summary of files read, searches performed, and hypotheses considered>. Manual investigation required." |
| Dev server not running for E2E | "Dev server is not running. Start it first: `make dev`" |
| E2E still failing after 3 iterations | "E2E tests are still failing after 3 fix attempts. Here are the remaining failures: <summary of failing pages and errors>. Manual investigation required." |
| No Copilot review after 20 iterations (10 minutes) | "No Copilot review received after 10 minutes. Do you want to keep waiting or skip to final output without Copilot feedback?" |
| CI still failing after 2 fix attempts | "CI is still failing after 2 fix attempts. Manual investigation required. Here are the full failing logs: <logs>" |
