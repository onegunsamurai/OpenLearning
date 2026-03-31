# Pipeline worked example

## Feature: "As a user, I want to reset my password via email"

This walks through exactly what each pipeline phase produces for a real feature.

---

### Phase 0 output: `docs/stories/password-reset/analysis.md`

```markdown
## Story summary
A registered user who has forgotten their password can request a reset link
sent to their registered email. Clicking the link opens a form to set a new
password. The link expires after 1 hour and can only be used once.

## Acceptance criteria

AC-1: GIVEN a registered user
      WHEN they submit their email on /forgot-password
      THEN a reset email is sent within 30 seconds
      AND a success message is shown (even if email not found — prevents enumeration)

AC-2: GIVEN a valid reset token
      WHEN the user clicks the link within 1 hour
      THEN they see a new password form

AC-3: GIVEN an expired or used token
      WHEN the user clicks the link
      THEN they see an "expired link" message with option to request a new one

AC-4: GIVEN the new password form
      WHEN the user submits a password meeting requirements (8+ chars, 1 uppercase, 1 number)
      THEN their password is updated AND all existing sessions are invalidated
      AND they are redirected to login

AC-5: GIVEN a valid reset token
      WHEN it is used once
      THEN it cannot be used again

## Edge cases
| Scenario | Expected behavior |
|----------|------------------|
| Email not in system | Show same success message (no enumeration) |
| Multiple rapid requests | Rate limit: max 3 per email per hour |
| User resets while logged in elsewhere | All sessions invalidated on reset |
| Token URL tampered with | 400 error, generic message |
| Password same as current | Reject with helpful message |
| SQL injection in email field | Input sanitized, no error leak |
| Concurrent reset requests | Last token wins, previous invalidated |

## Non-functional requirements
| Category | Requirement | Target |
|----------|-------------|--------|
| Performance | Reset email sent | < 30s p95 |
| Security | Token entropy | 256-bit cryptographic random |
| Security | Token storage | Hashed (bcrypt/argon2), not plaintext |
| Security | Rate limiting | 3 requests/email/hour, 10 requests/IP/hour |
| Accessibility | Form usable | Keyboard-only, screen reader, WCAG 2.1 AA |
| Observability | Metrics needed | reset_requested, reset_completed, reset_expired, reset_failed |

## Reuse candidates found in codebase
- `src/lib/email.ts` — existing email sending service (use this, don't create new)
- `src/middleware/rate-limit.ts` — existing rate limiter (extend, don't duplicate)
- `src/lib/crypto.ts` — existing token generation utilities

## Done conditions
- [ ] All 5 acceptance criteria pass as E2E tests
- [ ] Rate limiting active and tested
- [ ] Token stored hashed, verified in security review
- [ ] No email enumeration possible
- [ ] All sessions invalidated on password change
- [ ] Metrics: 4 counters instrumented and verified
- [ ] Docs: API endpoint documented, user-facing help text updated
```

---

### Phase 1 output: Architecture + Threat model + Schema

**Architect produces:**
- API contract: `POST /api/auth/forgot-password`, `POST /api/auth/reset-password`
- Component: new `PasswordResetService` using existing `EmailService` and `CryptoUtil`
- ADR: "Use database-stored hashed tokens instead of JWT-based stateless tokens because we need one-time-use enforcement"

**Threat modeler produces:**
- STRIDE finding: token enumeration (brute force) → mitigation: rate limiting + 256-bit tokens
- STRIDE finding: token interception (MITM) → mitigation: HTTPS-only, short expiry
- STRIDE finding: timing attack on token comparison → mitigation: constant-time comparison
- Security requirements fed to security-reviewer for Phase 4 validation

**Schema designer produces:**
```sql
-- Migration: add password_reset_tokens table
CREATE TABLE password_reset_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(255) NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_reset_tokens_hash ON password_reset_tokens(token_hash);
CREATE INDEX idx_reset_tokens_user ON password_reset_tokens(user_id);
```

**DESIGN GATE: PASS** — ADR reviewed, 0 critical threats unmitigated, contracts frozen.

---

### Phase 3-4 loop: TDD + Quality gate

**TDD guide writes tests first:**
```typescript
describe('PasswordResetService', () => {
  it('generates cryptographically secure token', async () => { /* ... */ });
  it('stores token hash, not plaintext', async () => { /* ... */ });
  it('rejects expired tokens', async () => { /* ... */ });
  it('invalidates token after single use', async () => { /* ... */ });
  it('invalidates all user sessions on reset', async () => { /* ... */ });
  it('rate limits requests per email', async () => { /* ... */ });
  it('returns same response for unknown emails', async () => { /* ... */ });
  it('uses constant-time comparison for token', async () => { /* ... */ });
});
```

Then implements code to make them pass. Then:

**Quality gate (5 agents parallel):**
- code-reviewer: PASS (clean separation, uses existing services)
- security-reviewer: PASS (tokens hashed, constant-time comparison, no enumeration)
- refactor-cleaner: PASS (no dead code introduced)
- perf-analyzer: PASS (indexed lookup, no N+1)
- a11y-auditor: PASS (form has labels, keyboard accessible, error messages linked)

**COMMIT GATE: PASS** → auto-commit: `feat: add password reset via email`

---

### Phase 5: Integration + E2E

**Integration tests:** real DB, real email (test SMTP):
```typescript
it('full reset flow: request → email → token → new password → session invalidation')
it('expired token returns 410 Gone')
it('rate limiter blocks 4th request in 1 hour')
```

**E2E tests (Playwright):** against running app:
```typescript
test('user can reset password from login page', async ({ page }) => {
  await page.goto('/login');
  await page.click('text=Forgot password?');
  await page.fill('[name=email]', 'user@test.com');
  await page.click('button[type=submit]');
  await expect(page.locator('.success-message')).toBeVisible();
  // ... follow reset link, set new password, verify login works
});
```

---

### Phase 6: Docs + Observability

**Doc updater:** API docs updated, codemap updated, CHANGELOG entry added.
**Observability checker:** verified 4 metrics counters, structured logging on all error paths, request tracing propagated.

**MERGE GATE: PASS** → PR ready with full summary.
```

---

This is what "expert-level engineering from an agentic pipeline" looks like in practice.
Every phase builds on the artifacts of the previous one.
Every gate enforces standards before moving forward.
