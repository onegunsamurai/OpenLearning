from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi import FastAPI
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import Base, User, get_db
from app.deps import JWT_ALGORITHM
from app.routes.auth import router as auth_router

# ── Test database setup ────────────────────────────────────────────────────

_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionFactory = async_sessionmaker(_test_engine, expire_on_commit=False)


async def _override_get_db():
    async with _TestSessionFactory() as session:
        yield session


# ── Test settings ──────────────────────────────────────────────────────────

_TEST_JWT_SECRET = "test-jwt-secret-key-for-tests"
_TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()
_TEST_GITHUB_CLIENT_ID = "test-client-id"
_TEST_GITHUB_CLIENT_SECRET = "test-client-secret"
_TEST_FRONTEND_URL = "http://localhost:3000"


def _mock_settings():
    from app.config import Settings

    return Settings(
        jwt_secret_key=_TEST_JWT_SECRET,
        encryption_key=_TEST_ENCRYPTION_KEY,
        github_client_id=_TEST_GITHUB_CLIENT_ID,
        github_client_secret=_TEST_GITHUB_CLIENT_SECRET,
        frontend_url=_TEST_FRONTEND_URL,
    )


# ── App + fixtures ─────────────────────────────────────────────────────────

_test_app = FastAPI()
_test_app.include_router(auth_router, prefix="/api/auth")
_test_app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def setup_db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_db) -> AsyncSession:
    async with _TestSessionFactory() as session:
        yield session


@pytest.fixture
def http_client(setup_db) -> AsyncClient:
    from httpx import ASGITransport

    transport = ASGITransport(app=_test_app)
    return AsyncClient(transport=transport, base_url="http://test")


def _make_jwt(
    user_id: str = "test-user-id",
    username: str = "testuser",
    avatar_url: str = "https://github.com/avatar.png",
    expired: bool = False,
) -> str:
    now = datetime.now(UTC)
    exp = now - timedelta(hours=1) if expired else now + timedelta(days=7)
    claims = {
        "sub": user_id,
        "username": username,
        "avatar_url": avatar_url,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(claims, _TEST_JWT_SECRET, algorithm=JWT_ALGORITHM)


async def _seed_user(
    db: AsyncSession, user_id: str = "test-user-id", github_id: int = 12345
) -> User:
    user = User(
        id=user_id,
        github_id=github_id,
        github_username="testuser",
        avatar_url="https://github.com/avatar.png",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ── Tests ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestGitHubOAuth:
    @patch("app.routes.auth.get_settings", _mock_settings)
    async def test_github_redirect_returns_302(self, http_client: AsyncClient, setup_db) -> None:
        resp = await http_client.get("/api/auth/github", follow_redirects=False)
        assert resp.status_code == 302
        location = resp.headers["location"]
        assert "github.com/login/oauth/authorize" in location
        assert "state=" in location

    @patch("app.routes.auth.get_settings", _mock_settings)
    @patch("app.deps.get_settings", _mock_settings)
    async def test_github_callback_creates_user_and_sets_cookie(
        self, http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Build a valid state
        from app.routes.auth import _sign_state

        state = _sign_state("/", _TEST_JWT_SECRET)

        # Mock the httpx calls to GitHub
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "gh-token-123"}

        mock_user_resp = MagicMock()
        mock_user_resp.json.return_value = {
            "id": 99999,
            "login": "newuser",
            "avatar_url": "https://avatars.githubusercontent.com/u/99999",
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_token_resp
        mock_client_instance.get.return_value = mock_user_resp
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routes.auth.httpx.AsyncClient", return_value=mock_client_instance):
            resp = await http_client.get(
                f"/api/auth/github/callback?code=test-code&state={state}",
                follow_redirects=False,
            )

        assert resp.status_code == 302
        assert "access_token" in resp.cookies

        # Verify user was created in DB
        from sqlalchemy import select

        result = await db_session.execute(select(User).where(User.github_id == 99999))
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.github_username == "newuser"

    @patch("app.routes.auth.get_settings", _mock_settings)
    @patch("app.deps.get_settings", _mock_settings)
    async def test_github_callback_upserts_existing_user(
        self, http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        # Pre-seed a user
        await _seed_user(db_session, user_id="existing-user", github_id=88888)

        from app.routes.auth import _sign_state

        state = _sign_state("/", _TEST_JWT_SECRET)

        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "gh-token-456"}

        mock_user_resp = MagicMock()
        mock_user_resp.json.return_value = {
            "id": 88888,
            "login": "updateduser",
            "avatar_url": "https://new-avatar.png",
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_token_resp
        mock_client_instance.get.return_value = mock_user_resp
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routes.auth.httpx.AsyncClient", return_value=mock_client_instance):
            resp = await http_client.get(
                f"/api/auth/github/callback?code=test-code&state={state}",
                follow_redirects=False,
            )

        assert resp.status_code == 302

        # Verify the existing user was updated, not duplicated
        from sqlalchemy import select

        result = await db_session.execute(select(User).where(User.github_id == 88888))
        user = result.scalar_one()
        assert user.github_username == "updateduser"
        assert user.avatar_url == "https://new-avatar.png"

    @patch("app.routes.auth.get_settings", _mock_settings)
    @patch("app.deps.get_settings", _mock_settings)
    async def test_github_callback_sanitizes_malicious_redirect_in_state(
        self, http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Regression: even if a malicious URL bypasses _validate_redirect on login,
        the inline urlparse().netloc guard in github_callback must sanitize it."""
        from app.routes.auth import _sign_state

        # Sign a malicious redirect directly into state (bypassing login-side validation)
        state = _sign_state("https://evil.com", _TEST_JWT_SECRET)

        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "gh-token-evil"}

        mock_user_resp = MagicMock()
        mock_user_resp.json.return_value = {
            "id": 77777,
            "login": "eviluser",
            "avatar_url": "https://avatars.githubusercontent.com/u/77777",
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_token_resp
        mock_client_instance.get.return_value = mock_user_resp
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routes.auth.httpx.AsyncClient", return_value=mock_client_instance):
            resp = await http_client.get(
                f"/api/auth/github/callback?code=test-code&state={state}",
                follow_redirects=False,
            )

        assert resp.status_code == 302
        location = resp.headers["location"]
        # Must redirect to safe frontend root, not to evil.com
        assert location == f"{_TEST_FRONTEND_URL}/"

    @patch("app.routes.auth.get_settings", _mock_settings)
    async def test_github_callback_invalid_code_returns_redirect_with_error(
        self, http_client: AsyncClient, setup_db
    ) -> None:
        from app.routes.auth import _sign_state

        state = _sign_state("/", _TEST_JWT_SECRET)

        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"error": "bad_verification_code"}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_token_resp
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.routes.auth.httpx.AsyncClient", return_value=mock_client_instance):
            resp = await http_client.get(
                f"/api/auth/github/callback?code=bad-code&state={state}",
                follow_redirects=False,
            )

        assert resp.status_code == 302
        assert "error=auth_failed" in resp.headers["location"]


@pytest.mark.asyncio
class TestAuthMe:
    @patch("app.routes.auth.get_settings", _mock_settings)
    @patch("app.deps.get_settings", _mock_settings)
    async def test_me_returns_user_with_valid_cookie(
        self, http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _seed_user(db_session)
        token = _make_jwt(user_id=user.id)
        resp = await http_client.get(
            "/api/auth/me",
            cookies={"access_token": token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["githubUsername"] == "testuser"
        assert data["userId"] == user.id

    @patch("app.deps.get_settings", _mock_settings)
    async def test_me_returns_401_without_cookie(self, http_client: AsyncClient, setup_db) -> None:
        resp = await http_client.get("/api/auth/me")
        assert resp.status_code == 401

    @patch("app.deps.get_settings", _mock_settings)
    async def test_me_returns_401_with_expired_token(
        self, http_client: AsyncClient, setup_db
    ) -> None:
        token = _make_jwt(expired=True)
        resp = await http_client.get(
            "/api/auth/me",
            cookies={"access_token": token},
        )
        assert resp.status_code == 401

    @patch("app.routes.auth.get_settings", _mock_settings)
    @patch("app.deps.get_settings", _mock_settings)
    async def test_me_has_api_key_false_when_no_key(
        self, http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _seed_user(db_session)
        token = _make_jwt(user_id=user.id)
        resp = await http_client.get(
            "/api/auth/me",
            cookies={"access_token": token},
        )
        assert resp.json()["hasApiKey"] is False

    @patch("app.routes.auth.get_settings", _mock_settings)
    @patch("app.deps.get_settings", _mock_settings)
    @patch("app.crypto.get_settings", _mock_settings)
    async def test_me_has_api_key_true_when_key_set(
        self, http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _seed_user(db_session)
        from app.crypto import encrypt_api_key

        user.encrypted_api_key = encrypt_api_key("sk-test")
        await db_session.commit()

        token = _make_jwt(user_id=user.id)
        resp = await http_client.get(
            "/api/auth/me",
            cookies={"access_token": token},
        )
        assert resp.json()["hasApiKey"] is True


@pytest.mark.asyncio
class TestLogout:
    async def test_logout_clears_cookie(self, http_client: AsyncClient, setup_db) -> None:
        resp = await http_client.post("/api/auth/logout")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Cookie should be deleted (max-age=0 or expires in the past)
        cookie_header = resp.headers.get("set-cookie", "")
        assert "access_token" in cookie_header


@pytest.mark.asyncio
class TestApiKey:
    @patch("app.routes.auth.get_settings", _mock_settings)
    @patch("app.routes.auth.encrypt_api_key")
    @patch("app.deps.get_settings", _mock_settings)
    async def test_set_api_key_stores_encrypted(
        self,
        mock_encrypt: MagicMock,
        http_client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        mock_encrypt.return_value = "encrypted-value"
        user = await _seed_user(db_session)
        token = _make_jwt(user_id=user.id)
        resp = await http_client.post(
            "/api/auth/api-key",
            json={"apiKey": "sk-my-secret-key"},
            cookies={"access_token": token},
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        mock_encrypt.assert_called_once_with("sk-my-secret-key")

    @patch("app.routes.auth.get_settings", _mock_settings)
    @patch("app.crypto.get_settings", _mock_settings)
    @patch("app.deps.get_settings", _mock_settings)
    async def test_get_api_key_returns_masked_preview(
        self, http_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _seed_user(db_session)
        from app.crypto import encrypt_api_key

        user.encrypted_api_key = encrypt_api_key("sk-ant-test1234")
        await db_session.commit()

        token = _make_jwt(user_id=user.id)
        resp = await http_client.get(
            "/api/auth/api-key",
            cookies={"access_token": token},
        )
        assert resp.status_code == 200
        preview = resp.json()["apiKeyPreview"]
        assert preview == "sk-...1234"

    @patch("app.deps.get_settings", _mock_settings)
    async def test_set_api_key_unauthenticated_returns_401(
        self, http_client: AsyncClient, setup_db
    ) -> None:
        resp = await http_client.post(
            "/api/auth/api-key",
            json={"apiKey": "sk-secret"},
        )
        assert resp.status_code == 401


class TestValidateRedirect:
    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("/dashboard", "/dashboard"),
            ("/", "/"),
            ("/assess?id=1", "/assess?id=1"),
            ("", "/"),
            ("http://evil.com", "/"),
            ("//evil.com", "/"),
            ("/\\evil.com", "/"),
            ("javascript:alert(1)", "/"),
            (None, "/"),
            ("relative/path", "/"),
            ("/path#fragment", "/path#fragment"),
            ("https://evil.com/path", "/"),
        ],
    )
    def test_validate_redirect(self, input_val: str | None, expected: str) -> None:
        from app.routes.auth import _validate_redirect

        assert _validate_redirect(input_val) == expected
