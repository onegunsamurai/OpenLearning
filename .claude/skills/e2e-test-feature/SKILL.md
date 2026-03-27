---
name: e2e-test-feature
description: E2E test the current feature/fix using Playwright MCP browser automation
---

# Feature-Focused E2E Testing

Test the feature or fix on the current branch using Playwright MCP browser automation. Gathers context from git and issues, plans which pages/flows to test, executes interactively, and reports results formatted for the next fix iteration.

## Steps

### 1. Gather Context

```bash
git branch --show-current
git log --oneline -10
git diff main...HEAD --name-only
```

- Identify the current branch name and parse it for feature context (e.g., `feat/fix-login-redirect` means test login redirect).
- Read the recent commits to understand what changed.
- List all files changed vs main to determine scope.
- Extract any issue numbers from branch name or commit messages (e.g., `#123`). If found, read the issue:
  ```bash
  gh issue view <number>
  ```
- If on `main` or no changes exist, ask the user what specific flow to test before proceeding.

### 2. Plan Test Flow

Map changed files to pages that need testing:

| Changed File Pattern | URL to Test |
|---------------------|-------------|
| `frontend/src/app/page.tsx` | `/` |
| `frontend/src/app/login/**` | `/login` |
| `frontend/src/app/assess/**` | `/assess` |
| `frontend/src/app/dashboard/**` | `/dashboard` |
| `frontend/src/app/gap-analysis/**` | `/gap-analysis` |
| `frontend/src/app/learning-plan/**` | `/learning-plan` |
| `frontend/src/app/demo/**` | `/demo/assess`, `/demo/report` |
| `frontend/src/app/export/**` | `/export/[id]` |
| `frontend/src/components/**` | All pages importing the component |
| `frontend/src/hooks/**` | All pages using the hook |
| `frontend/src/lib/**` | All pages using the module |
| `backend/app/routes/**` | Frontend pages that call those API routes |

Read the relevant page objects in `frontend/e2e/pages/*.page.ts` to understand the expected element selectors for each page.

Determine which pages require authentication:
- **Public (no auth):** `/`, `/login`, `/demo/assess`, `/demo/report`
- **Auth required:** `/dashboard`, `/assess`, `/gap-analysis`, `/learning-plan`, `/export/[id]`

### 3. Pre-flight Check

Navigate to `http://localhost:3000` using `mcp__playwright__browser_navigate`. If it fails to load, tell the user to run `make dev` and stop.

If any auth-required pages are in the test plan:
1. Navigate to `http://localhost:3000/login`
2. Use `mcp__playwright__browser_snapshot` to verify the login form loaded
3. Click the "Sign In" tab via `mcp__playwright__browser_click`
4. Fill email `$E2E_TEST_EMAIL` and password `$E2E_TEST_PASSWORD` (from env vars) using `mcp__playwright__browser_fill_form`
5. Click the "Sign In" button via `mcp__playwright__browser_click`
6. Wait for redirect to `/dashboard` using `mcp__playwright__browser_wait_for`
7. If login fails (user not registered), first register via the Register tab with the same credentials, then sign in

### 4. Execute Tests

For each page in the test plan, run this sequence:

1. **Navigate:** `mcp__playwright__browser_navigate` to `http://localhost:3000/<path>`
2. **Wait:** `mcp__playwright__browser_wait_for` for the page's key elements (reference the page object selectors)
3. **Snapshot:** `mcp__playwright__browser_snapshot` — verify expected elements are present in the accessibility tree
4. **Console check:** `mcp__playwright__browser_console_messages` — flag any `error` level messages
5. **Network check:** `mcp__playwright__browser_network_requests` — flag any 4xx/5xx responses that are not expected
6. **Screenshot:** `mcp__playwright__browser_take_screenshot` — save to `e2e-screenshots/feat-NN-<page-name>.png`
7. **Feature interactions:** Based on the feature context, interact with the specific elements that changed:
   - Use `mcp__playwright__browser_click` for buttons, tabs, links
   - Use `mcp__playwright__browser_fill_form` for form inputs
   - Use `mcp__playwright__browser_type` for text inputs like chat
   - Use `mcp__playwright__browser_press_key` for keyboard actions (Enter to submit)
8. **Post-interaction verify:** Take another snapshot and screenshot to confirm the expected state change occurred

### 5. Close Browser

After all tests complete, use `mcp__playwright__browser_close` to clean up.

## Output Format

```
## E2E Test Results: <branch-name>

### Context
- **Branch:** <branch-name>
- **Feature:** <description from issue or commits>
- **Related issue:** <#number and title, or "none">
- **Pages tested:** <comma-separated list>

### Results

| # | Page | Test | Status | Details |
|---|------|------|--------|---------|
| 1 | /login | Page loads | PASS | All form elements visible |
| 2 | /login | Sign in flow | PASS | Redirects to /dashboard |
| 3 | /dashboard | Console errors | FAIL | TypeError: Cannot read property 'map' of undefined |

### Console Errors
| Page | Level | Message |
|------|-------|---------|
(deduplicated — omit this section if none found)

### Network Errors
| Page | URL | Status | Method |
|------|-----|--------|--------|
(omit this section if none found)

### Screenshots
1. `e2e-screenshots/feat-01-login.png` — Login page after load
2. `e2e-screenshots/feat-02-dashboard.png` — Dashboard after sign in

### Recommended Next Steps
- <actionable fix 1 based on failures, with file:line reference if possible>
- <actionable fix 2>
(omit this section if all tests pass)
```
