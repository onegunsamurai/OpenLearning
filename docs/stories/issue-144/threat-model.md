# Threat Model: Issue #144 — Success State UIs for Perfect Scores

**Date:** 2026-04-01
**Scope:** Frontend-only UI change — new success state components for gap analysis and learning plan pages when a user has zero skill gaps (100% scores).
**Backend changes:** None. No new API endpoints, no schema changes, no new data flows.

---

## 1. Architecture Overview

### Components affected

| Component | Change description |
|---|---|
| `AssessmentComplete.tsx` | Extract `SkillScoreCard` sub-component (refactor, no new logic) |
| `gap-analysis/page.tsx` | Add conditional branch when `gapAnalysis.gaps.length === 0` to render success state |
| New: `NoGapsSuccess` component | Renders congratulatory UI with CTAs for learning-plan page |
| New success state in gap-analysis | Renders congratulatory UI with CTAs ("Try a harder level", "Add more skills", "Share your results") |

### Data flow (unchanged)

```
Browser → (Next.js rewrite) → /api/assessment/report/{sessionId} → Backend → DB
                                        ↓
                              AssessmentReportResponse
                              (gapAnalysis.gaps[], proficiencyScores[], learningPlan)
                                        ↓
                              Frontend renders based on gaps.length
```

No new data flows are introduced. The existing `useSessionReport` hook fetches the same `AssessmentReportResponse` and the frontend conditionally renders either the existing gap-cards view or the new success state based on `gaps.length === 0`.

### Trust boundaries (unchanged)

1. **User browser <-> Next.js server** — TLS in production, session cookies
2. **Next.js rewrite proxy <-> FastAPI backend** — internal network, CORS-restricted
3. **FastAPI backend <-> Database** — parameterized queries via SQLAlchemy

This change does NOT cross any new trust boundaries.

---

## 2. Trust Boundaries

No new trust boundaries are introduced. All data rendered in the new success state components originates from the same authenticated API response (`AssessmentReportResponse`) that the existing gap-analysis and learning-plan pages already consume.

---

## 3. STRIDE Analysis

### 3.1 STRIDE Matrix

| Threat | Component | Risk | Analysis |
|---|---|---|---|
| **Spoofing** | New UI components | **N/A** | No new auth surfaces. Pages already require authentication via `useAuth`/`useAuthStore` with redirect to `/login` if unauthenticated. No change needed. |
| **Tampering** | CTA navigation links | **LOW** | CTAs use `router.push()` for internal navigation. An attacker cannot tamper with these since they are hardcoded paths, not user-supplied. |
| **Tampering** | "Share your results" CTA | **LOW** | If implemented via `navigator.share()` or clipboard copy, the data copied is the user's own assessment data. No server-side mutation. |
| **Repudiation** | New UI states | **N/A** | No new actions that require audit trails. Viewing a success page is a read-only operation. |
| **Information Disclosure** | Rendered skill names, scores | **LOW** | Skill names (`skillName`) and scores (`score`, `overallReadiness`) come from LLM-generated backend responses. These are already displayed on existing pages. React's JSX auto-escapes text content, preventing injection. The data is the authenticated user's own data. |
| **Information Disclosure** | "Share your results" CTA | **MEDIUM** | If "Share your results" exposes a shareable URL or copies data to clipboard, it could inadvertently leak the user's assessment data (skill names, scores, session ID). This is the primary concern for this change. |
| **Denial of Service** | New components | **N/A** | No new API calls, no new server-side processing. Purely presentational. |
| **Elevation of Privilege** | New components | **N/A** | No authorization changes. The same `useSessionReport(sessionId)` hook is used, and the backend enforces ownership checks on the report endpoint. |

### 3.2 Detailed threat analysis

#### T-1: XSS via LLM-generated content rendered in success state (LOW)

**Description:** The `skillName`, `recommendation`, and `summary` fields in `GapAnalysis` and `ProficiencyScore` types are LLM-generated strings. If the success state renders any of these (e.g., listing skill names in a "You mastered:" list), there is a theoretical XSS vector if the LLM output contains malicious HTML/JS.

**Current mitigation:** React's JSX rendering auto-escapes all text content placed in `{}` expressions. The existing codebase renders these fields via `{gap.skillName}`, `{gap.recommendation}`, `{score.skillName}`, and `{summary}` — all safely escaped by React.

**Risk:** LOW — React's built-in escaping handles this. The risk would only materialize if `dangerouslySetInnerHTML` were used, which the codebase does not use (confirmed by grep: only one test file reference to `innerHTML`).

**Requirement:** Do NOT use `dangerouslySetInnerHTML` in new components. Continue using standard JSX text interpolation.

#### T-2: Session ID exposure via "Share your results" CTA (MEDIUM)

**Description:** The proposed "Share your results" CTA could expose the user's `sessionId` (a UUID) in a shared URL, clipboard content, or social media post. The session ID is used to fetch the full assessment report via `/api/assessment/report/{sessionId}`. If the report endpoint does not enforce ownership (i.e., anyone with the session ID can fetch the report), sharing the session ID effectively shares all assessment data.

**Current state:** The `useSessionReport` hook calls `api.assessmentReport(sessionId)` which hits a backend endpoint. Need to verify the backend enforces that only the session owner can access the report.

**Risk:** MEDIUM — The session ID is already present in the URL query parameter (`?session=<uuid>`) on the gap-analysis and learning-plan pages. The "Share" CTA does not introduce new exposure beyond what URL bar visibility already provides, but it makes sharing more intentional and likely.

**Requirement:** (1) If "Share your results" copies/shares a URL containing the session ID, the backend MUST enforce ownership on the report endpoint. (2) Alternatively, the "Share" CTA can share only a static congratulatory message without session-specific data or URLs.

#### T-3: Open redirect via CTA navigation (LOW)

**Description:** CTAs like "Try a harder level" and "Add more skills" use `router.push()` with hardcoded internal paths. No user-supplied input controls the navigation target.

**Risk:** LOW — No open redirect risk since paths are hardcoded in the component source.

**Requirement:** CTAs must use hardcoded paths or paths derived from application state (not URL parameters or user input).

---

## 4. Attack Surface Inventory

| Entry point | Type | Auth required | Change in this issue |
|---|---|---|---|
| `/gap-analysis?session=<id>` | Page route | Yes (redirect to login) | Modified: adds success-state rendering branch |
| `/learning-plan?session=<id>` | Page route | Yes (redirect to login) | Modified: adds success-state rendering branch |
| `AssessmentComplete` component | UI component | Yes (parent page enforces) | Modified: extract `SkillScoreCard` sub-component |
| "Share your results" CTA | User action | Yes (on authenticated page) | **NEW**: copies data to clipboard or triggers Web Share API |
| "Try a harder level" CTA | Navigation | Yes (on authenticated page) | **NEW**: `router.push()` to internal route |
| "Add more skills" CTA | Navigation | Yes (on authenticated page) | **NEW**: `router.push()` to internal route |

**No new API endpoints.** No new backend routes. No new data fetching. No new external integrations.

---

## 5. Security Requirements

### SR-1: No dangerouslySetInnerHTML in new components
- **Priority:** HIGH
- **Threat:** T-1 (XSS via LLM-generated content)
- **CWE:** CWE-79 (Improper Neutralization of Input During Web Page Generation)
- **OWASP:** A03:2021 — Injection
- **Mitigation:** All LLM-generated content (skill names, scores, summaries) must be rendered via standard React JSX text interpolation `{value}`, never via `dangerouslySetInnerHTML`.
- **Validation:** Grep new component files for `dangerouslySetInnerHTML`, `innerHTML`, or `__html`. Zero matches required.

### SR-2: Share CTA must not expose session-bound URLs without backend authorization
- **Priority:** MEDIUM
- **Threat:** T-2 (Session ID exposure via share)
- **CWE:** CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor), CWE-639 (Authorization Bypass Through User-Controlled Key)
- **OWASP:** A01:2021 — Broken Access Control
- **Mitigation:** The "Share your results" CTA should either: (a) share only a generic congratulatory message without session-specific URLs or data, or (b) if sharing a URL, confirm the backend report endpoint enforces that only the authenticated session owner can access it (i.e., returns 403/404 for other users).
- **Implementation note:** Prefer option (a) for this issue — share a static message like "I scored 100% on [skill area] on OpenLearning!" without exposing session IDs or report URLs. The Web Share API (`navigator.share()`) or `navigator.clipboard.writeText()` are both acceptable.
- **Validation:** Review the share CTA implementation. Verify no session ID or report URL is included in shared content. If a URL is shared, verify backend authorization test exists for the report endpoint.

### SR-3: CTA navigation uses hardcoded internal paths only
- **Priority:** LOW
- **Threat:** T-3 (Open redirect)
- **CWE:** CWE-601 (URL Redirection to Untrusted Site)
- **OWASP:** A01:2021 — Broken Access Control
- **Mitigation:** All CTA buttons must navigate using `router.push()` with hardcoded string paths (e.g., `router.push("/")`, `router.push("/dashboard")`). No user-supplied input (query params, form fields) should control navigation targets.
- **Validation:** Review CTA click handlers. All `router.push()` calls must use string literals or paths derived from trusted application state (`sessionId` from authenticated API response is acceptable for internal navigation).

### SR-4: No new dependencies with known vulnerabilities
- **Priority:** LOW
- **Threat:** Supply chain
- **CWE:** CWE-1395 (Dependency on Vulnerable Third-Party Component)
- **OWASP:** A06:2021 — Vulnerable and Outdated Components
- **Mitigation:** This change should not require new npm dependencies. If any are added (e.g., for share functionality), they must be vetted for known vulnerabilities.
- **Validation:** Compare `package.json` before and after. If new deps added, run `npm audit`.

---

## 6. Existing Security Patterns (to reuse)

### Authentication guard
Both `gap-analysis/page.tsx` and `learning-plan/page.tsx` already implement the auth guard pattern:
```tsx
const { user, isLoading: authLoading } = useAuthStore();
const { login } = useAuth();

useEffect(() => {
  if (!authLoading && !user) {
    login("/gap-analysis" + (sessionParam ? `?session=${sessionParam}` : ""));
  }
}, [authLoading, user, login, sessionParam]);

if (authLoading || !user) return null;
```
The new success-state branches render inside these same pages, so they inherit this guard automatically. No additional auth work needed.

### React JSX auto-escaping
All existing components render LLM-generated text via JSX interpolation (`{value}`). Examples:
- `GapCard.tsx` line 31: `{gap.skillName}`, line 52: `{gap.recommendation}`
- `GapSummary.tsx` line 79: `{summary}`
- `AssessmentComplete.tsx` line 48: `{score.skillName}`, line 52: `{score.reasoning}`

This pattern must be continued in new components.

### CORS configuration
Backend restricts origins via `settings.cors_origins` (not `*`). This is already in place and requires no changes.

### Session ID handling
Session IDs are UUIDs passed as URL query parameters. The pattern of `searchParams.get("session")` with fallback to Zustand store state is established and safe. The new components do not introduce new session handling logic.

### No `dangerouslySetInnerHTML` usage
The codebase has zero instances of `dangerouslySetInnerHTML` in production code. This is a strong existing pattern to maintain.

---

## 7. Risk Summary

| Risk | Rating | Blocking? | Notes |
|---|---|---|---|
| XSS via LLM content | LOW | No | React auto-escapes; just maintain existing pattern |
| Session ID leak via Share | MEDIUM | No | Design the share CTA to avoid exposing session IDs |
| Open redirect via CTAs | LOW | No | Hardcoded paths; no user input controls navigation |
| New dependency vulns | LOW | No | No new deps expected |

**Overall assessment:** This is a low-risk, frontend-only presentational change. There are no CRITICAL threats. The only MEDIUM-priority item is the "Share your results" CTA design, which should be addressed by sharing a generic message rather than session-specific URLs. No changes block architecture approval.
