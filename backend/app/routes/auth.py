from __future__ import annotations

import logging
import uuid
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import AuthMethod, User, get_db
from app.deps import AuthUser, get_current_user
from app.models.auth import (
    AuthMeResponse,
    LoginRequest,
    OkResponse,
    RegisterRequest,
)
from app.repositories import user_repo
from app.services import auth_service

logger = logging.getLogger("openlearning.auth")

router = APIRouter()


# ── Routes ─────────────────────────────────────────────────────────────────


@router.get("/github")
async def github_login(redirect: str = Query(default="/")) -> RedirectResponse:
    """Redirect the user to GitHub OAuth authorization."""
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")

    redirect_path = auth_service.validate_redirect(redirect)
    state = auth_service.sign_oauth_state(redirect_path, settings.jwt_secret_key)

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.frontend_url.rstrip('/')}/api/auth/github/callback",
        "scope": "read:user",
        "state": state,
    }
    url = f"{auth_service.GITHUB_AUTHORIZE_URL}?{urlencode(params)}"
    return RedirectResponse(url=url, status_code=302)  # codeql[py/url-redirection]


@router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle the GitHub OAuth callback: exchange code, upsert user, set JWT cookie."""
    settings = get_settings()
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=501, detail="GitHub OAuth is not configured")

    # Verify state
    try:
        redirect_path = auth_service.verify_oauth_state(state, settings.jwt_secret_key)
    except ValueError:
        logger.warning("Invalid OAuth state parameter")
        return RedirectResponse(url=f"{settings.frontend_url}/?error=auth_failed", status_code=302)

    redirect_path = auth_service.validate_redirect(redirect_path)

    # Exchange code for GitHub user profile
    user_data = await auth_service.exchange_github_token(
        code, settings.github_client_id, settings.github_client_secret
    )
    if not user_data:
        return RedirectResponse(url=f"{settings.frontend_url}/?error=auth_failed", status_code=302)

    github_id = user_data.get("id")
    github_username = user_data.get("login", "")
    avatar_url = user_data.get("avatar_url", "")

    if not github_id:
        return RedirectResponse(url=f"{settings.frontend_url}/?error=auth_failed", status_code=302)

    # Upsert user via AuthMethod
    auth_method = await user_repo.get_auth_method(db, "github", str(github_id))
    if auth_method:
        user = await user_repo.get_user_by_auth_method(db, auth_method)
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
    token = auth_service.create_jwt(user, settings.jwt_secret_key)
    final_url = f"{settings.frontend_url}{redirect_path}"
    parsed_final = urlparse(final_url)
    parsed_base = urlparse(settings.frontend_url)
    if parsed_final.netloc != parsed_base.netloc:
        final_url = settings.frontend_url
    response = RedirectResponse(url=final_url, status_code=302)
    auth_service.set_auth_cookie(response, token, settings.frontend_url)
    return response


@router.get("/me", response_model=AuthMeResponse, response_model_by_alias=True)
async def auth_me(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuthMeResponse:
    """Return the current user's profile."""
    db_user = await user_repo.get_user_or_404(db, user.user_id)
    has_api_key = bool(db_user.encrypted_api_key)

    email: str | None = None
    email_method = await user_repo.get_auth_method_by_user(db, db_user.id, "email")
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


@router.post("/register", response_model=OkResponse, response_model_by_alias=True)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Register a new user with email and password."""
    settings = get_settings()
    user = await auth_service.register_user(db, request.email, request.password)
    token = auth_service.create_jwt(user, settings.jwt_secret_key)
    response = JSONResponse(content={"ok": True})
    auth_service.set_auth_cookie(response, token, settings.frontend_url)
    return response


@router.post("/login", response_model=OkResponse, response_model_by_alias=True)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Authenticate with email and password."""
    settings = get_settings()
    user = await auth_service.authenticate_user(db, request.email, request.password)
    token = auth_service.create_jwt(user, settings.jwt_secret_key)
    response = JSONResponse(content={"ok": True})
    auth_service.set_auth_cookie(response, token, settings.frontend_url)
    return response
