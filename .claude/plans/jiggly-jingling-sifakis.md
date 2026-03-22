# Documentation Sync: Email/Password Auth Feature

## Context

The email/password authentication feature added `POST /register`, `POST /login`, `AuthMethod` table, and renamed `github_username` → `display_name`. Documentation was not updated to reflect these changes. This plan fixes the 6 discrepancies found by auditing code against docs.

---

## Findings Summary

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | **HIGH** | `docs/guides/api-reference.md` | Missing `POST /register` and `POST /login` endpoints |
| 2 | **HIGH** | `docs/guides/api-reference.md:67,184` | `AuthMeResponse` shows `githubUsername` — should be `displayName` + missing `email` field |
| 3 | **HIGH** | `docs/architecture/data-models.md:478-488` | `users` table still shows `github_id`/`github_username` columns; missing `auth_methods` table entirely |
| 4 | **MEDIUM** | `docs/architecture/data-models.md:474` | Says "three tables" — now four (added `auth_methods`) |
| 5 | **MEDIUM** | `docs/architecture/data-models.md:515-518` | Relationships section missing `User → AuthMethod` |
| 6 | **LOW** | `docs/development/testing.md:27-52,136-154` | Missing `test_password.py` (backend) and `login/page.test.tsx` (frontend) |

No issues found in: assessment-pipeline.md, overview.md, knowledge-base.md, setup.md, code-style.md, mkdocs.yml nav. `mkdocs build --strict` passes clean.

---

## Fix 1: Add register/login endpoints to API reference

**File:** `docs/guides/api-reference.md`

Insert after the `GET /api/auth/github/callback` section (after line 54), before `GET /api/auth/me`:

- `POST /api/auth/register` — document request body (`RegisterRequest`: `email`, `password`), response `{"ok": true}` with `access_token` cookie, error codes 400 (password length), 409 (duplicate email), 422 (invalid email)
- `POST /api/auth/login` — document request body (`LoginRequest`: `email`, `password`), response `{"ok": true}` with `access_token` cookie, error code 401

## Fix 2: Update AuthMeResponse in API reference

**File:** `docs/guides/api-reference.md`

**Lines 64-70** — Update JSON example:
- `"githubUsername"` → `"displayName"`
- Add `"email": null` field

**Lines 182-186** — Update Python model block:
- `github_username: str` → `display_name: str`
- Add `email: str | None = None`

Also add `RegisterRequest` and `LoginRequest` models to the Auth Models code block (after line 196).

## Fix 3: Update `users` table schema in data-models

**File:** `docs/architecture/data-models.md`

**Line 474** — Change "three tables" → "four tables"

**Lines 478-488** — Replace the `users` table with actual columns:
| Column | Type | Description |
|--------|------|-------------|
| `id` | `String(36)` PK | UUID user identifier |
| `display_name` | `String(100)` | User display name |
| `avatar_url` | `String(500)` | Avatar URL |
| `encrypted_api_key` | `String(500)` NULL | Fernet-encrypted Anthropic API key |
| `created_at` | `DateTime` | Creation timestamp |
| `updated_at` | `DateTime` | Last update timestamp |

**After line 488** — Add new `auth_methods` table:
| Column | Type | Description |
|--------|------|-------------|
| `id` | `Integer` PK | Auto-incrementing ID |
| `user_id` | `String(36)` FK | References `users.id` |
| `provider` | `String(20)` | Auth provider: `"github"` or `"email"` |
| `provider_id` | `String(320)` | Provider-specific ID (GitHub user ID or email address) |
| `credential` | `String(500)` NULL | Hashed password (email provider only) |
| `created_at` | `DateTime` | Creation timestamp |

**Lines 515-518** — Add to Relationships:
- `User` → `AuthMethod`: one-to-many via `user_id` (cascade delete-orphan)

## Fix 4: Add missing test files to testing docs

**File:** `docs/development/testing.md`

**Line 33** (backend tree) — Add after `test_auth_guard.py`:
```
├── test_password.py           # Password hashing and verification tests
```

**Line 153** (frontend tree) — Add after `learning-plan/`:
```
│   ├── login/
│   │   └── page.test.tsx
```

---

## Files Changed

| File | Fixes |
|------|-------|
| `docs/guides/api-reference.md` | #1, #2 |
| `docs/architecture/data-models.md` | #3 |
| `docs/development/testing.md` | #4 |

## Verification

1. `mkdocs build --strict` — no broken links or warnings
2. Spot-check: every field name, type, and endpoint in updated docs matches the code in `backend/app/db.py`, `backend/app/routes/auth.py`
