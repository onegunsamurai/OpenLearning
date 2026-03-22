---
name: security
description: Security rules for authentication, data handling, secrets, and API boundaries
globs: []
---

# Security Rules

## Secrets and Credentials
- Never hardcode secrets, tokens, or API keys — use environment variables
- Never log sensitive data (passwords, tokens, API keys, user PII)
- Never commit `.env` files, `.pem` keys, or credential files

## Database
- Use parameterized queries via SQLAlchemy ORM — never construct raw SQL strings
- Use SQLAlchemy's `text()` with bound parameters if raw SQL is unavoidable

## Authentication and Authorization
- Use `bcrypt` for password hashing (match `backend/app/password.py`)
- Use Fernet for symmetric encryption (match `backend/app/crypto.py`)
- Rate-limit authentication endpoints (login, register, password reset)
- If cookies are introduced: set `httponly`, `secure`, `samesite=lax` flags

## Input Validation
- Validate all user input at API boundaries using Pydantic models
- Return `HTTPException(400)` for invalid data — never pass unsanitized input downstream
- Sanitize any user-provided content rendered in SSE streams to prevent XSS

## CORS
- Only allow configured origins (match `backend/app/main.py` CORS middleware)
- Never use `allow_origins=["*"]` in production configuration

## Dependencies
- Pin dependency versions in `requirements.txt` and `package.json`
- Review new dependencies for known vulnerabilities before adding
