---
name: e2e-test-general
description: Exploratory QA testing across all pages — finds bugs and files GitHub issues
---

# Exploratory E2E Testing

Act as a human QA tester. Systematically walk through every page of the application, testing common functionality and interactions. Collect all bugs found, present them to the user, and file GitHub issues only if the user confirms.

## Steps

### 1. Pre-flight Check

1. Navigate to `http://localhost:3000` using `mcp__playwright__browser_navigate`. If it fails to load, tell the user to run `make dev` and stop.
2. Health-check the backend: use `mcp__playwright__browser_evaluate` to run `fetch('http://localhost:8000/api/health').then(r => r.status)`. If not `200`, tell the user the backend is down and stop.

### 2. Phase A — Public Pages (No Auth Required)

Test each page in order. For every page: navigate, snapshot, screenshot, check console messages, check network requests, then interact.

#### 2.1 Landing Page (`/`)

1. `mcp__playwright__browser_navigate` to `http://localhost:3000`
2. `mcp__playwright__browser_snapshot` — verify:
   - Hero heading is present
   - Role selector is visible
   - "Start Assessment" button exists and is **disabled** (no skills selected)
   - "Try Interactive Demo" link is visible
3. `mcp__playwright__browser_take_screenshot` → `e2e-screenshots/gen-01-landing.png`
4. **Test interaction:** Click a role card → verify topic chips/cards appear in the snapshot → verify "Start Assessment" button becomes enabled
5. `mcp__playwright__browser_console_messages` — flag any errors
6. `mcp__playwright__browser_take_screenshot` → `e2e-screenshots/gen-02-landing-role-selected.png`

#### 2.2 Demo Assessment (`/demo/assess`)

1. Navigate to `http://localhost:3000/demo/assess`
2. Snapshot — verify:
   - Chat interface is visible
   - An initial AI message is present (or onboarding dialog)
3. `mcp__playwright__browser_take_screenshot` → `e2e-screenshots/gen-03-demo-assess.png`
4. **Test interaction:** If onboarding dialog appears, dismiss it. Type a test response in the chat input and submit (press Enter). Verify the message appears in the chat history.
5. Check console messages for errors

#### 2.3 Demo Report (`/demo/report`)

1. Navigate to `http://localhost:3000/demo/report`
2. Snapshot — verify:
   - Gap analysis content or tab is visible
   - Radar chart area or gap cards are present
3. `mcp__playwright__browser_take_screenshot` → `e2e-screenshots/gen-04-demo-report.png`
4. **Test interaction:** If there are tabs (e.g., "Gap Analysis" / "Learning Plan"), click the second tab and verify content switches
5. Check console messages for errors

#### 2.4 Login Page (`/login`)

1. Navigate to `http://localhost:3000/login`
2. Snapshot — verify:
   - "Sign In" and "Register" tabs exist
   - Email and password inputs are visible
   - GitHub OAuth button is present
3. `mcp__playwright__browser_take_screenshot` → `e2e-screenshots/gen-05-login.png`
4. **Test interaction — Register tab:** Click "Register" tab → verify "Confirm password" field appears
5. **Test interaction — Invalid login:** Click "Sign In" tab → fill email `invalid@test.com` and password `wrong` → click "Sign In" → verify error message appears
6. `mcp__playwright__browser_take_screenshot` → `e2e-screenshots/gen-06-login-error.png`
7. **Test interaction — Valid login:** Fill email `e2e-test@openlearning.test` and password `TestPassword123!` → click "Sign In" → wait for redirect to `/dashboard`
8. Check console messages for errors

### 3. Phase B — Authenticated Pages (After Login)

Continue testing after successful login from step 2.4.

#### 3.1 Dashboard (`/dashboard`)

1. Navigate to `http://localhost:3000/dashboard` (should already be here after login)
2. Snapshot — verify:
   - "Your Assessments" heading (or similar)
   - Profile/user info card
   - "New Assessment" button or link
   - Either assessment history cards or an empty state message
3. `mcp__playwright__browser_take_screenshot` → `e2e-screenshots/gen-07-dashboard.png`
4. Check console messages for errors
5. Note any session IDs visible (needed for gap-analysis/learning-plan tests)

#### 3.2 Assessment (`/assess`)

1. Navigate back to `http://localhost:3000` (landing page)
2. Select a role and at least one topic to enable the "Start Assessment" button
3. Click "Start Assessment"
4. Snapshot — verify:
   - Chat interface is visible with heading
   - Input field is enabled
   - An initial message or loading state is present
5. `mcp__playwright__browser_take_screenshot` → `e2e-screenshots/gen-08-assess.png`
6. Check console messages for errors
7. **Do NOT run a full assessment** — just verify the page loads and the interface is functional

#### 3.3 Gap Analysis (`/gap-analysis`)

1. If a session ID was found in the dashboard (step 3.1), navigate to `http://localhost:3000/gap-analysis?sessionId=<id>` or however the app routes to it
2. If no session ID is available, navigate to `http://localhost:3000/gap-analysis` and verify the page handles the missing session gracefully (redirect or error message, not a crash)
3. Snapshot and screenshot → `e2e-screenshots/gen-09-gap-analysis.png`
4. Check console messages for errors

#### 3.4 Learning Plan (`/learning-plan`)

1. Same approach as Gap Analysis — use session ID if available, otherwise verify graceful handling
2. Snapshot and screenshot → `e2e-screenshots/gen-10-learning-plan.png`
3. Check console messages for errors

### 4. Cross-cutting Checks

After testing all pages:

1. **Console errors:** Compile all console errors from all pages into a deduplicated list (group by message, note which pages)
2. **Network failures:** Compile all failed network requests (4xx/5xx) across all pages
3. **Missing elements:** Note any pages where expected elements were not found in the snapshot
4. **Unexpected states:** Note any pages showing error messages, blank content, or loading spinners that never resolve

### 5. Close Browser

Use `mcp__playwright__browser_close` to clean up.

### 6. Present Findings

Present the full test report (see Output Format below) to the user.

If bugs were found, classify each by severity:
- **Critical:** Page crash, JS error preventing interaction, broken auth flow
- **High:** Missing functionality, broken navigation, API errors
- **Medium:** UI glitches, missing elements that don't block the flow
- **Low:** Console warnings, minor visual issues

Then ask the user: **"I found N bugs. Would you like me to file these as GitHub issues?"**

Only proceed to step 7 if the user confirms.

### 7. File GitHub Issues (Only If User Confirms)

Before filing, check for existing open bug issues:
```bash
gh issue list --label bug --state open --limit 50
```

For each distinct bug, skip if a similar issue already exists. Otherwise create:
```bash
gh issue create \
  --title "[Bug] <concise description>" \
  --label "bug" \
  --body "## Description
<clear description of the bug>

## Steps to Reproduce
1. Navigate to <URL>
2. <action taken>
3. <what was observed>

## Expected Behavior
<what should have happened>

## Actual Behavior
<what actually happened — include error messages>

## Environment
- OS: macOS (E2E test via Playwright MCP)
- Browser: Chromium (Playwright)
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

## Additional Context
- Console errors: <if any>
- Screenshot: <path to screenshot>
- Found by: /e2e-test-general automated exploratory testing"
```

## Output Format

```
## Exploratory E2E Test Report

### Summary
- **Pages tested:** N
- **Bugs found:** N (N critical, N high, N medium, N low)
- **Issues created:** N (or "pending user confirmation")
- **Console errors:** N unique errors across N pages
- **Network errors:** N failed requests

### Page Results

| # | Page | Status | Issues Found |
|---|------|--------|--------------|
| 1 | / (Landing) | PASS | None |
| 2 | /demo/assess | WARN | 1 console warning |
| 3 | /login | PASS | None |
| 4 | /dashboard | FAIL | Missing assessment cards |
| ... | ... | ... | ... |

### Bugs Found

| # | Title | Severity | Page | Details |
|---|-------|----------|------|---------|
| 1 | Login error shows [object Object] | High | /login | Error message renders raw object instead of text |
| ... | ... | ... | ... | ... |

### Bugs Filed (after user confirmation)

| # | Issue | Title | Severity |
|---|-------|-------|----------|
| 1 | #NNN | [Bug] Login error shows [object Object] | High |
| ... | ... | ... | ... |

### Console Errors (deduplicated)

| Message | Pages | Count |
|---------|-------|-------|
| TypeError: Cannot read property 'x' of undefined | /dashboard, /assess | 2 |

### Screenshots
1. `e2e-screenshots/gen-01-landing.png`
2. `e2e-screenshots/gen-02-landing-role-selected.png`
3. ...
```
