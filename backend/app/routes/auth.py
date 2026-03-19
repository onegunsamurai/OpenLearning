from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crypto import decrypt_api_key, encrypt_api_key
from app.db import User, get_db
from app.deps import JWT_ALGORITHM, AuthUser, get_current_user
from app.models.base import CamelModel

logger = logging.getLogger("openlearning.auth")

router = APIRouter()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
JWT_EXPIRY_DAYS = 7


# ── Response models ────────────────────────────────────────────────────────


class AuthMeResponse(CamelModel):
    user_id: str
    github_username: str
    avatar_url: str
    has_api_key: bool


class ApiKeySetRequest(CamelModel):
    api_key: str


class ApiKeyResponse(CamelModel):
    api_key_preview: str


# ── Helpers ────────────────────────────────────────────────────────────────


def _sign_state(payload: str, secret: str) -> str:
    """Return 'payload.signature' where signature is HMAC-SHA256 hex digest."""
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify_state(state: str, secret: str) -> str:
    """Verify HMAC signature and return the original payload. Raises ValueError."""
    if "." not in state:
        raise ValueError("Malformed state parameter")
    payload, sig = state.rsplit(".", 1)
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("Invalid state signature")
    return payload


def _validate_redirect(redirect: str) -> str:
    """Ensure redirect path is safe (starts with /, no //)."""
    if not redirect or not redirect.startswith("/") or redirect.startswith("//"):
        return "/"
    return redirect


def _create_jwt(user: User, secret: str) -> str:
    """Create a signed JWT for the given user."""
    now = datetime.now(UTC)
    claims = {
        "sub": user.id,
        "username": user.github_username,
        "avatar_url": user.avatar_url,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRY_DAYS),
    }
    return jwt.encode(claims, secret, algorithm=JWT_ALGORITHM)


def _is_secure(frontend_url: str) -> bool:
    """Return True if the frontend URL uses HTTPS (production)."""
    return frontend_url.startswith("https://")


# ── Routes ─────────────────────────────────────────────────────────────────


@router.get("/github")
async def github_login(redirect: str = Query(default="/")) -> RedirectResponse:
    """Redirect the user to GitHub OAuth authorization."""
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")

    redirect_path = _validate_redirect(redirect)
    state = _sign_state(redirect_path, settings.jwt_secret_key)

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.frontend_url.rstrip('/')}/api/auth/github/callback",
        "scope": "read:user",
        "state": state,
    }
    url = f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url=url, status_code=302)


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle the GitHub OAuth callback: exchange code, upsert user, set JWT cookie."""
    settings = get_settings()
    if not settings.github_client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")

    # Verify state
    try:
        redirect_path = _verify_state(state, settings.jwt_secret_key)
    except ValueError:
        logger.warning("Invalid OAuth state parameter")
        return RedirectResponse(url=f"{settings.frontend_url}/?error=auth_failed", status_code=302)

    redirect_path = _validate_redirect(redirect_path)

    # Exchange code for access token
    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                GITHUB_TOKEN_URL,
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            token_data = token_resp.json()
            gh_access_token = token_data.get("access_token")
            if not gh_access_token:
                logger.warning("GitHub token exchange failed: %s", token_data)
                return RedirectResponse(
                    url=f"{settings.frontend_url}/?error=auth_failed", status_code=302
                )

            # Fetch user profile
            user_resp = await client.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {gh_access_token}",
                    "Accept": "application/json",
                },
            )
            user_data = user_resp.json()
    except httpx.HTTPError:
        logger.exception("GitHub API request failed")
        return RedirectResponse(url=f"{settings.frontend_url}/?error=auth_failed", status_code=302)

    github_id = user_data.get("id")
    github_username = user_data.get("login", "")
    avatar_url = user_data.get("avatar_url", "")

    if not github_id:
        return RedirectResponse(url=f"{settings.frontend_url}/?error=auth_failed", status_code=302)

    # Upsert user
    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()
    if user:
        user.github_username = github_username
        user.avatar_url = avatar_url
    else:
        user = User(
            id=str(uuid.uuid4()),
            github_id=github_id,
            github_username=github_username,
            avatar_url=avatar_url,
        )
        db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create JWT and set cookie
    token = _create_jwt(user, settings.jwt_secret_key)
    response = RedirectResponse(url=f"{settings.frontend_url}{redirect_path}", status_code=302)
    secure = _is_secure(settings.frontend_url)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
        max_age=JWT_EXPIRY_DAYS * 24 * 60 * 60,
    )
    return response


@router.get("/me", response_model=AuthMeResponse, response_model_by_alias=True)
async def auth_me(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthMeResponse:
    """Return the current user's profile."""
    result = await db.execute(select(User).where(User.id == user.user_id))
    db_user = result.scalar_one_or_none()
    has_api_key = bool(db_user and db_user.encrypted_api_key)
    return AuthMeResponse(
        user_id=user.user_id,
        github_username=user.github_username,
        avatar_url=user.avatar_url,
        has_api_key=has_api_key,
    )


@router.post("/logout")
async def auth_logout() -> JSONResponse:
    """Clear the auth cookie."""
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie(key="access_token", path="/")
    return resp


@router.post("/api-key")
async def set_api_key(
    request: ApiKeySetRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Store an encrypted API key for the current user."""
    result = await db.execute(select(User).where(User.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.encrypted_api_key = encrypt_api_key(request.api_key)
    await db.commit()
    return {"ok": True}


@router.get("/api-key", response_model=ApiKeyResponse, response_model_by_alias=True)
async def get_api_key(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    """Return a masked preview of the stored API key."""
    result = await db.execute(select(User).where(User.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if not db_user or not db_user.encrypted_api_key:
        raise HTTPException(status_code=404, detail="No API key stored")
    # Decrypt to get last 4 chars for preview
    plaintext = decrypt_api_key(db_user.encrypted_api_key)
    preview = f"sk-...{plaintext[-4:]}" if len(plaintext) >= 4 else "sk-...****"
    return ApiKeyResponse(api_key_preview=preview)
