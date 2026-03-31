from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AuthMethod, User


async def get_user_by_id(
    db: AsyncSession,
    user_id: str,
) -> User | None:
    """Fetch a user by primary key."""
    return await db.get(User, user_id)


async def get_user_or_404(
    db: AsyncSession,
    user_id: str,
) -> User:
    """Fetch a user by ID, raising 404 if not found."""
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_auth_method(
    db: AsyncSession,
    provider: str,
    provider_id: str,
) -> AuthMethod | None:
    """Find an auth method by provider + provider_id."""
    result = await db.execute(
        select(AuthMethod).where(
            AuthMethod.provider == provider,
            AuthMethod.provider_id == provider_id,
        )
    )
    return result.scalar_one_or_none()


async def get_auth_method_by_user(
    db: AsyncSession,
    user_id: str,
    provider: str,
) -> AuthMethod | None:
    """Find an auth method by user_id + provider."""
    result = await db.execute(
        select(AuthMethod).where(
            AuthMethod.user_id == user_id,
            AuthMethod.provider == provider,
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_auth_method(
    db: AsyncSession,
    auth_method: AuthMethod,
) -> User:
    """Fetch the user associated with an auth method. Raises 404 if missing."""
    result = await db.execute(select(User).where(User.id == auth_method.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
