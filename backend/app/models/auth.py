from __future__ import annotations

from pydantic import EmailStr

from app.models.base import CamelModel


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
