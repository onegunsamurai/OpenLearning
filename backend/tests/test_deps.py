"""Tests for the get_user_api_key dependency."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import Base, User, get_db
from app.deps import get_user_api_key
from tests.conftest import _test_db_url

# ── Test database setup ────────────────────────────────────────────────

_test_engine = create_async_engine(_test_db_url, poolclass=NullPool)
_TestSessionFactory = async_sessionmaker(_test_engine, expire_on_commit=False)

# ── Test settings ──────────────────────────────────────────────────────

_TEST_JWT_SECRET = "test-jwt-secret-for-deps"
_TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()


def _mock_settings():
    from app.config import Settings

    return Settings(
        jwt_secret_key=_TEST_JWT_SECRET,
        encryption_key=_TEST_ENCRYPTION_KEY,
    )


async def _override_get_db():
    async with _TestSessionFactory() as session:
        yield session


# ── App + fixtures ─────────────────────────────────────────────────────

_test_app = FastAPI()
_test_app.dependency_overrides[get_db] = _override_get_db


@_test_app.get("/test-key")
async def _test_key_route(api_key: str = Depends(get_user_api_key)) -> dict:
    return {"key": api_key}


@pytest_asyncio.fixture
async def setup_db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_db) -> AsyncSession:
    async with _TestSessionFactory() as session:
        yield session


def _make_jwt(user_id: str = "dep-test-user") -> str:
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.deps import JWT_ALGORITHM

    now = datetime.now(UTC)
    claims = {
        "sub": user_id,
        "username": "testuser",
        "avatar_url": "",
        "iat": now,
        "exp": now + timedelta(days=7),
    }
    return jwt.encode(claims, _TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── Tests ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGetUserApiKey:
    @patch("app.deps.get_settings", _mock_settings)
    @patch("app.crypto.get_settings", _mock_settings)
    async def test_returns_decrypted_key(self, db_session: AsyncSession) -> None:
        from app.crypto import encrypt_api_key

        user = User(id="dep-test-user", github_id=11111, github_username="test", avatar_url="")
        user.encrypted_api_key = encrypt_api_key("sk-my-secret")
        db_session.add(user)
        await db_session.commit()

        token = _make_jwt()
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/test-key", cookies={"access_token": token})
        assert resp.status_code == 200
        assert resp.json()["key"] == "sk-my-secret"

    @patch("app.deps.get_settings", _mock_settings)
    async def test_no_key_returns_400(self, db_session: AsyncSession) -> None:
        user = User(id="dep-test-user", github_id=11111, github_username="test", avatar_url="")
        db_session.add(user)
        await db_session.commit()

        token = _make_jwt()
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/test-key", cookies={"access_token": token})
        assert resp.status_code == 400

    @patch("app.deps.get_settings", _mock_settings)
    async def test_no_user_returns_400(self, setup_db) -> None:
        token = _make_jwt(user_id="nonexistent-user")
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/test-key", cookies={"access_token": token})
        assert resp.status_code == 400

    @patch("app.deps.get_settings", _mock_settings)
    async def test_corrupt_key_returns_500(self, db_session: AsyncSession) -> None:
        """Corrupted/invalid ciphertext should return 500 with a helpful message."""
        user = User(id="dep-test-user", github_id=11111, github_username="test", avatar_url="")
        user.encrypted_api_key = "not-valid-fernet-ciphertext"
        db_session.add(user)
        await db_session.commit()

        token = _make_jwt()
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            resp = await client.get("/test-key", cookies={"access_token": token})
        assert resp.status_code == 500
        assert "re-save" in resp.json()["detail"].lower()
