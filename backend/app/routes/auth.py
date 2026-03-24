from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from jose import jwt
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crypto import decrypt_api_key, encrypt_api_key
from app.db import AuthMethod, User, get_db
from app.deps import JWT_ALGORITHM, AuthUser, get_current_user
from app.models.base import CamelModel
from app.password import hash_password, verify_password

logger = logging.getLogger("openlearning.auth")

router = APIRouter()

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
JWT_EXPIRY_DAYS = 7

_DUMMY_BCRYPT_HASH = hash_password("timing-equalization-dummy")


# ── Response models ────────────────────────────────────────────────────────


class AuthMeResponse(CamelModel):
    user_id: str
    display_name: str
    avatar_url: str
    has_api_key: bool
    email: str | None = None


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str


class LoginRequest(CamelModel):
    email: EmailStr
    password: str


class ApiKeySetRequest(CamelModel):
    api_key: str


class ApiKeyResponse(CamelModel):
    api_key_preview: str


class OkResponse(CamelModel):
    ok: bool


class ValidateKeyResponse(CamelModel):
    valid: bool
    error: str | None = None


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
    """Ensure redirect is a safe relative path (no scheme, no netloc, no backslashes)."""
    if not redirect or not redirect.startswith("/"):
        return "/"
    # Reject protocol-relative URLs, backslash tricks, and encoded variants
    if redirect.startswith("//") or "\\" in redirect:
        return "/"
    parsed = urlparse(redirect)
    if parsed.scheme or parsed.netloc:
        return "/"
    # Return only the path (+ query/fragment if present), stripping any injected authority
    safe = parsed.path
    if parsed.query:
        safe += f"?{parsed.query}"
    if parsed.fragment:
        safe += f"#{parsed.fragment}"
    return safe if safe.startswith("/") else "/"


def _create_jwt(user: User, secret: str) -> str:
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
    # Redirect target is always the hardcoded GITHUB_AUTHORIZE_URL constant;
    # user input only appears in the state query parameter value.
    return RedirectResponse(url=url, status_code=302)  # codeql[py/url-redirection]


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
                logger.warning(
                    "GitHub token exchange failed: error=%s description=%s",
                    token_data.get("error"),
                    token_data.get("error_description"),
                )
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

    # Upsert user via AuthMethod
    result = await db.execute(
        select(AuthMethod).where(
            AuthMethod.provider == "github", AuthMethod.provider_id == str(github_id)
        )
    )
    auth_method = result.scalar_one_or_none()
    if auth_method:
        user_result = await db.execute(select(User).where(User.id == auth_method.user_id))
        user = user_result.scalar_one()
        user.display_name = github_username
        user.avatar_url = avatar_url
    else:
        user = User(
            id=str(uuid.uuid4()),
            display_name=github_username,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.flush()
        db.add(
            AuthMethod(
                user_id=user.id,
                provider="github",
                provider_id=str(github_id),
            )
        )
    await db.commit()
    await db.refresh(user)

    # Create JWT and set cookie
    token = _create_jwt(user, settings.jwt_secret_key)
    final_url = f"{settings.frontend_url}{redirect_path}"
    parsed_final = urlparse(final_url)
    parsed_base = urlparse(settings.frontend_url)
    if parsed_final.netloc != parsed_base.netloc:
        final_url = settings.frontend_url
    response = RedirectResponse(url=final_url, status_code=302)
    _set_auth_cookie(response, token, settings.frontend_url)
    return response


@router.get("/me", response_model=AuthMeResponse, response_model_by_alias=True)
async def auth_me(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthMeResponse:
    """Return the current user's profile."""
    result = await db.execute(select(User).where(User.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    has_api_key = bool(db_user.encrypted_api_key)

    # Find email from auth_methods if present
    email: str | None = None
    am_result = await db.execute(
        select(AuthMethod).where(AuthMethod.user_id == db_user.id, AuthMethod.provider == "email")
    )
    email_method = am_result.scalar_one_or_none()
    if email_method:
        email = email_method.provider_id

    return AuthMeResponse(
        user_id=user.user_id,
        display_name=db_user.display_name,
        avatar_url=db_user.avatar_url,
        has_api_key=has_api_key,
        email=email,
    )


@router.post("/logout")
async def auth_logout() -> JSONResponse:
    """Clear the auth cookie."""
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie(key="access_token", path="/")
    return resp


@router.post("/api-key", response_model=OkResponse, response_model_by_alias=True)
async def set_api_key(
    request: ApiKeySetRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OkResponse:
    """Store an encrypted API key for the current user."""
    result = await db.execute(select(User).where(User.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.encrypted_api_key = encrypt_api_key(request.api_key)
    await db.commit()
    return OkResponse(ok=True)


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


@router.delete("/api-key", response_model=OkResponse, response_model_by_alias=True)
async def delete_api_key(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OkResponse:
    """Remove the stored API key for the current user."""
    result = await db.execute(select(User).where(User.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if db_user:
        db_user.encrypted_api_key = None
        await db.commit()
    return OkResponse(ok=True)


@router.post("/validate-key", response_model=ValidateKeyResponse, response_model_by_alias=True)
async def validate_key(
    request: ApiKeySetRequest,
    user: AuthUser = Depends(get_current_user),
) -> ValidateKeyResponse:
    """Validate an Anthropic API key without storing it."""
    import anthropic

    try:
        client = anthropic.AsyncAnthropic(api_key=request.api_key)
        await client.models.list(limit=1)
        return ValidateKeyResponse(valid=True)
    except anthropic.AuthenticationError:
        return ValidateKeyResponse(valid=False, error="Invalid API key")
    except anthropic.RateLimitError:
        return ValidateKeyResponse(valid=False, error="Rate limited — key may be valid")
    except Exception:
        logger.exception("Key validation failed")
        return ValidateKeyResponse(valid=False, error="Validation failed")


# ── Email/Password Auth ───────────────────────────────────────────────


def _set_auth_cookie(
    response: JSONResponse | RedirectResponse, token: str, frontend_url: str
) -> None:
    """Set the JWT auth cookie on a JSON response."""
    secure = _is_secure(frontend_url)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
        max_age=JWT_EXPIRY_DAYS * 24 * 60 * 60,
    )


@router.post("/register", response_model=OkResponse, response_model_by_alias=True)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Register a new user with email and password."""
    settings = get_settings()

    # Validate password length
    if len(request.password) < 8 or len(request.password) > 128:
        raise HTTPException(status_code=400, detail="Password must be between 8 and 128 characters")

    email = request.email.lower()

    # Check for existing email auth method
    result = await db.execute(
        select(AuthMethod).where(AuthMethod.provider == "email", AuthMethod.provider_id == email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    # Create user + auth method
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
            credential=hash_password(request.password),
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

    # Set JWT cookie
    token = _create_jwt(user, settings.jwt_secret_key)
    response = JSONResponse(content={"ok": True})
    _set_auth_cookie(response, token, settings.frontend_url)
    return response


@router.post("/login", response_model=OkResponse, response_model_by_alias=True)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Authenticate with email and password."""
    settings = get_settings()
    email = request.email.lower()

    result = await db.execute(
        select(AuthMethod).where(AuthMethod.provider == "email", AuthMethod.provider_id == email)
    )
    auth_method = result.scalar_one_or_none()
    if not auth_method or not auth_method.credential:
        verify_password("", _DUMMY_BCRYPT_HASH)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(request.password, auth_method.credential):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_result = await db.execute(select(User).where(User.id == auth_method.user_id))
    user = user_result.scalar_one()

    token = _create_jwt(user, settings.jwt_secret_key)
    response = JSONResponse(content={"ok": True})
    _set_auth_cookie(response, token, settings.frontend_url)
    return response
