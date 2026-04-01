"""Auth service — business logic extracted from routes/auth.py."""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from jose import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AuthMethod, User
from app.deps import JWT_ALGORITHM
from app.password import hash_password, verify_password
from app.repositories import user_repo

logger = logging.getLogger("openlearning.auth_service")

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
JWT_EXPIRY_DAYS = 7

_DUMMY_BCRYPT_HASH = hash_password("timing-equalization-dummy")


# ── Pure helpers ──────────────────────────────────────────────────────────


def sign_oauth_state(payload: str, secret: str) -> str:
    """Return 'payload.signature' where signature is HMAC-SHA256 hex digest."""
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_oauth_state(state: str, secret: str) -> str:
    """Verify HMAC signature and return the original payload. Raises ValueError."""
    if "." not in state:
        raise ValueError("Malformed state parameter")
    payload, sig = state.rsplit(".", 1)
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("Invalid state signature")
    return payload


def validate_redirect(redirect: str | None) -> str:
    """Ensure redirect is a safe relative path (no scheme, no netloc, no backslashes)."""
    if not redirect or not redirect.startswith("/"):
        return "/"
    if redirect.startswith("//") or "\\" in redirect:
        return "/"
    parsed = urlparse(redirect)
    if parsed.scheme or parsed.netloc:
        return "/"
    safe = parsed.path
    if parsed.query:
        safe += f"?{parsed.query}"
    if parsed.fragment:
        safe += f"#{parsed.fragment}"
    return safe if safe.startswith("/") else "/"


def create_jwt(user: User, secret: str) -> str:
    """Create a signed JWT for the given user."""
    now = datetime.now(UTC)
    claims = {
        "sub": user.id,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)


def set_auth_cookie(
    response: JSONResponse | RedirectResponse, token: str, frontend_url: str
) -> None:
    """Set the JWT auth cookie on a response."""
    secure = frontend_url.startswith("https://")
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
        max_age=JWT_EXPIRY_DAYS * 24 * 60 * 60,
    )


# ── Async service functions ──────────────────────────────────────────────


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    """Register a new user with email and password.

    Validates password length, checks for duplicates, creates User + AuthMethod.
    Raises HTTPException(400) for invalid password, HTTPException(409) for duplicate email.
    """
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=400, detail="Password must be between 8 and 128 characters")

    email = email.lower()

    if await user_repo.get_auth_method(db, "email", email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    email_prefix = email.split("@")[0]
    user = User(
        id=str(uuid.uuid4()),
        display_name=email_prefix,
        avatar_url="",
    )
    db.add(user)
    await db.flush()
    db.add(
        AuthMethod(
            user_id=user.id,
            provider="email",
            provider_id=email,
            credential=hash_password(password),
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists"
        ) from None
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    """Authenticate a user with email and password.

    Uses timing-safe comparison to prevent user enumeration.
    Raises HTTPException(401) on invalid credentials.
    """
    email = email.lower()

    auth_method = await user_repo.get_auth_method(db, "email", email)
    if not auth_method or not auth_method.credential:
        verify_password("", _DUMMY_BCRYPT_HASH)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(password, auth_method.credential):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return await user_repo.get_user_by_auth_method(db, auth_method)


async def exchange_github_token(code: str, client_id: str, client_secret: str) -> dict | None:
    """Exchange a GitHub OAuth code for user profile data.

    Returns the GitHub user dict, or None if the exchange failed.
    """
    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                GITHUB_TOKEN_URL,
                json={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            token_data = token_resp.json()
            gh_access_token = token_data.get("access_token")
            if not gh_access_token:
                logger.warning(
                    "GitHub token exchange failed: error=%s description=%s",
                    token_data.get("error"),
                    token_data.get("error_description"),
                )
                return None

            user_resp = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {gh_access_token}",
                    "Accept": "application/json",
                },
            )
            return user_resp.json()
    except httpx.HTTPError:
        logger.exception("GitHub API request failed")
        return None
