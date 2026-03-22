from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.crypto import decrypt_api_key
from app.db import User, get_db

JWT_ALGORITHM = "HS256"


class AuthUser:
    """Lightweight user identity extracted from a JWT. Not a Pydantic model."""

    __slots__ = ("avatar_url", "display_name", "user_id")

    def __init__(self, user_id: str, display_name: str, avatar_url: str) -> None:
        self.user_id = user_id
        self.display_name = display_name
        self.avatar_url = avatar_url


async def get_current_user(
    access_token: str | None = Cookie(default=None),
) -> AuthUser:
    """Decode the JWT cookie and return an AuthUser. Raises 401 if missing or invalid."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise HTTPException(status_code=401, detail="Authentication is not configured")
    try:
        payload = jwt.decode(access_token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token claims")
    return AuthUser(
        user_id=user_id,
        display_name=payload.get("display_name", ""),
        avatar_url=payload.get("avatar_url", ""),
    )


async def get_optional_user(
    access_token: str | None = Cookie(default=None),
) -> AuthUser | None:
    """Like get_current_user but returns None instead of raising 401."""
    if not access_token:
        return None
    settings = get_settings()
    if not settings.jwt_secret_key:
        return None
    try:
        payload = jwt.decode(access_token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return AuthUser(
        user_id=user_id,
        display_name=payload.get("display_name", ""),
        avatar_url=payload.get("avatar_url", ""),
    )


async def get_user_api_key(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Return the decrypted API key for the current user. Raises 400 if not configured."""
    result = await db.execute(select(User).where(User.id == user.user_id))
    db_user = result.scalar_one_or_none()
    if not db_user or not db_user.encrypted_api_key:
        raise HTTPException(
            status_code=400,
            detail="No API key configured. Please add your Anthropic API key in Settings.",
        )
    try:
        return decrypt_api_key(db_user.encrypted_api_key)
    except ValueError as exc:
        # Encryption key misconfigured or stored API key is invalid/corrupted.
        raise HTTPException(
            status_code=500,
            detail=(
                "There was a problem loading your saved API key. "
                "Please re-save your Anthropic API key in Settings."
            ),
        ) from exc
