"""API key management routes — CRUD for user API keys."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto import decrypt_api_key, encrypt_api_key
from app.db import get_db
from app.deps import AuthUser, get_current_user
from app.models.auth import (
    ApiKeyResponse,
    ApiKeySetRequest,
    OkResponse,
    ValidateKeyResponse,
)
from app.repositories import user_repo

logger = logging.getLogger("openlearning.api_keys")

router = APIRouter()


@router.post("/api-key", response_model=OkResponse, response_model_by_alias=True)
async def set_api_key(
    request: ApiKeySetRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OkResponse:
    """Store an encrypted API key for the current user."""
    db_user = await user_repo.get_user_or_404(db, user.user_id)
    db_user.encrypted_api_key = encrypt_api_key(request.api_key)
    await db.commit()
    return OkResponse(ok=True)


@router.get(
    "/api-key",
    response_model=ApiKeyResponse,
    response_model_by_alias=True,
    responses={204: {"description": "No API key stored"}},
)
async def get_api_key(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse | Response:
    """Return a masked preview of the stored API key."""
    db_user = await user_repo.get_user_by_id(db, user.user_id)
    if not db_user or not db_user.encrypted_api_key:
        return Response(status_code=204)
    plaintext = decrypt_api_key(db_user.encrypted_api_key)
    preview = f"sk-...{plaintext[-4:]}" if len(plaintext) >= 4 else "sk-...****"
    return ApiKeyResponse(api_key_preview=preview)


@router.delete("/api-key", response_model=OkResponse, response_model_by_alias=True)
async def delete_api_key(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OkResponse:
    """Remove the stored API key for the current user."""
    db_user = await user_repo.get_user_by_id(db, user.user_id)
    if db_user:
        db_user.encrypted_api_key = None
        await db.commit()
    return OkResponse(ok=True)


@router.post("/validate-key", response_model=ValidateKeyResponse, response_model_by_alias=True)
async def validate_key(
    request: ApiKeySetRequest,
    _user: AuthUser = Depends(get_current_user),
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
