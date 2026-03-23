from __future__ import annotations

import pytest

# ── Test app with materials router ──────────────────────────────────────
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db import MaterialResult, get_db
from app.deps import get_current_user, get_user_api_key
from app.routes.materials import router as materials_router
from tests.conftest import (
    _override_get_current_user,
    _override_get_db,
    _override_get_user_api_key,
    _TestSessionFactory,
    seed_session,
)

_materials_test_app = FastAPI()
_materials_test_app.include_router(materials_router, prefix="/api")
_materials_test_app.dependency_overrides[get_db] = _override_get_db
_materials_test_app.dependency_overrides[get_current_user] = _override_get_current_user
_materials_test_app.dependency_overrides[get_user_api_key] = _override_get_user_api_key


# ── Seed helpers ────────────────────────────────────────────────────────


async def seed_material(
    session_id: str = "sess-001",
    concept_id: str = "http_fundamentals",
    domain: str = "backend_engineering",
    bloom_score: float = 0.9,
    quality_score: float = 0.85,
    quality_flag: str | None = None,
) -> None:
    async with _TestSessionFactory() as db:
        db.add(
            MaterialResult(
                session_id=session_id,
                concept_id=concept_id,
                domain=domain,
                bloom_score=bloom_score,
                quality_score=quality_score,
                iteration_count=1,
                quality_flag=quality_flag,
                material={
                    "concept_id": concept_id,
                    "target_bloom": 2,
                    "sections": [{"type": "explanation", "title": "Test", "body": "Test content"}],
                    "bloom_score": bloom_score,
                    "quality_score": quality_score,
                    "iteration_count": 1,
                },
            )
        )
        await db.commit()


class TestMaterialsRoute:
    @pytest.mark.asyncio
    async def test_get_materials_success(self, setup_db) -> None:
        async with _TestSessionFactory() as db:
            await seed_session(db, "sess-mat", "thread-mat", "completed")

        await seed_material(session_id="sess-mat")

        async with AsyncClient(
            transport=ASGITransport(app=_materials_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/materials/sess-mat")

        assert response.status_code == 200
        data = response.json()
        assert data["sessionId"] == "sess-mat"
        assert len(data["materials"]) == 1
        assert data["materials"][0]["conceptId"] == "http_fundamentals"
        assert data["materials"][0]["bloomScore"] == 0.9

    @pytest.mark.asyncio
    async def test_get_materials_with_quality_flag(self, setup_db) -> None:
        async with _TestSessionFactory() as db:
            await seed_session(db, "sess-flag", "thread-flag", "completed")

        await seed_material(
            session_id="sess-flag",
            bloom_score=0.5,
            quality_flag="max_iterations_reached",
        )

        async with AsyncClient(
            transport=ASGITransport(app=_materials_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/materials/sess-flag")

        assert response.status_code == 200
        data = response.json()
        assert data["materials"][0]["qualityFlag"] == "max_iterations_reached"

    @pytest.mark.asyncio
    async def test_get_materials_session_not_found(self, setup_db) -> None:
        async with AsyncClient(
            transport=ASGITransport(app=_materials_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/materials/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_materials_empty_in_progress(self, setup_db) -> None:
        async with _TestSessionFactory() as db:
            await seed_session(db, "sess-prog", "thread-prog", "completed")

        async with AsyncClient(
            transport=ASGITransport(app=_materials_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/materials/sess-prog")

        assert response.status_code == 200
        data = response.json()
        assert data["sessionId"] == "sess-prog"
        assert data["materials"] == []
