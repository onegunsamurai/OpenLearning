from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.routes.assessment import router as assessment_router
from app.routes.auth import router as auth_router
from app.routes.gap_analysis import router as gap_analysis_router
from app.routes.health import router as health_router
from app.routes.learning_plan import router as learning_plan_router
from app.routes.roles import router as roles_router
from app.routes.skills import router as skills_router

# ── Separate test app WITHOUT get_current_user override ────────────────────

_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSessionFactory = async_sessionmaker(_test_engine, expire_on_commit=False)


async def _override_get_db():
    async with _TestSessionFactory() as session:
        yield session


_TEST_JWT_SECRET = "guard-test-secret"


def _mock_settings():
    from app.config import Settings

    return Settings(jwt_secret_key=_TEST_JWT_SECRET)


def _mock_settings_empty_secret():
    from app.config import Settings

    return Settings(jwt_secret_key="")


_guard_app = FastAPI()
_guard_app.include_router(assessment_router, prefix="/api")
_guard_app.include_router(gap_analysis_router, prefix="/api")
_guard_app.include_router(learning_plan_router, prefix="/api")
_guard_app.include_router(auth_router, prefix="/api/auth")
_guard_app.include_router(health_router, prefix="/api")
_guard_app.include_router(skills_router, prefix="/api")
_guard_app.include_router(roles_router, prefix="/api")
_guard_app.dependency_overrides[get_db] = _override_get_db

# Provide a mock graph object for assessment routes
_mock_graph = AsyncMock()
_guard_app.state.graph = _mock_graph


@pytest_asyncio.fixture
async def setup_db():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(setup_db) -> AsyncClient:
    transport = ASGITransport(app=_guard_app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── Protected routes should return 401 without auth ────────────────────────


@pytest.mark.asyncio
@patch("app.deps.get_settings", _mock_settings)
class TestProtectedRoutesReturn401:
    async def test_assessment_start_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/assessment/start",
            json={"skillIds": ["react"], "targetLevel": "mid"},
        )
        assert resp.status_code == 401

    async def test_assessment_respond_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/assessment/fake-session/respond",
            json={"response": "test"},
        )
        assert resp.status_code == 401

    async def test_gap_analysis_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/gap-analysis",
            json={
                "proficiencyScores": [
                    {"skillId": "react", "skillName": "React", "score": 70, "confidence": 0.8}
                ]
            },
        )
        assert resp.status_code == 401

    async def test_learning_plan_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/learning-plan",
            json={"gapAnalysis": {"overallReadiness": 50, "gaps": [], "summary": "test"}},
        )
        assert resp.status_code == 401

    async def test_auth_me_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_auth_set_api_key_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post("/api/auth/api-key", json={"apiKey": "sk-test"})
        assert resp.status_code == 401

    async def test_auth_get_api_key_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/auth/api-key")
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestEmptyJwtSecret:
    """Verify that an empty JWT secret rejects forged tokens instead of accepting them."""

    @patch("app.deps.get_settings", _mock_settings_empty_secret)
    async def test_forged_token_rejected_when_secret_empty(self, client: AsyncClient) -> None:
        """A JWT signed with an empty string must be rejected when jwt_secret_key is empty."""
        from jose import jwt as jose_jwt

        from app.deps import JWT_ALGORITHM

        forged_token = jose_jwt.encode(
            {"sub": "attacker", "username": "evil", "avatar_url": ""},
            "",
            algorithm=JWT_ALGORITHM,
        )
        resp = await client.get(
            "/api/auth/me",
            cookies={"access_token": forged_token},
        )
        assert resp.status_code == 401


# ── Public routes should remain accessible ─────────────────────────────────


@pytest.mark.asyncio
class TestPublicRoutesAccessible:
    async def test_health_is_public(self, client: AsyncClient) -> None:
        resp = await client.get("/api/health")
        assert resp.status_code == 200

    async def test_skills_is_public(self, client: AsyncClient) -> None:
        resp = await client.get("/api/skills")
        assert resp.status_code == 200

    async def test_roles_is_public(self, client: AsyncClient) -> None:
        resp = await client.get("/api/roles")
        assert resp.status_code == 200
