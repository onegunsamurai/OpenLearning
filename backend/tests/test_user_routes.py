"""Tests for user routes (list assessments, delete assessment)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import AssessmentResult, AssessmentSession, MaterialResult, User
from tests.conftest import (
    _test_app,
    _TestSessionFactory,
    seed_result,
    seed_session,
)


class TestListUserAssessments:
    @pytest.mark.asyncio
    async def test_list_empty(self, setup_db):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/user/assessments")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_sessions(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db, session_id="sess-list-1")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/user/assessments")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sessionId"] == "sess-list-1"
        assert data[0]["skillCount"] == 1

    @pytest.mark.asyncio
    async def test_list_includes_role_id(self, setup_db):
        async with _TestSessionFactory() as db:
            session = AssessmentSession(
                session_id="sess-role-1",
                thread_id="thread-role-1",
                skill_ids=["react"],
                target_level="mid",
                role_id="frontend_engineering",
                status="active",
                user_id="test-user-id",
            )
            db.add(session)
            await db.commit()

        with patch("app.routes.user.load_knowledge_base") as mock_kb:
            mock_kb.return_value.display_name = "Frontend Engineer"
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.get("/api/user/assessments")

        data = response.json()
        assert data[0]["roleId"] == "frontend_engineering"
        assert data[0]["roleName"] == "Frontend Engineer"

    @pytest.mark.asyncio
    async def test_list_null_role_id(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/user/assessments")

        data = response.json()
        assert data[0]["roleId"] is None
        assert data[0]["roleName"] is None

    @pytest.mark.asyncio
    async def test_list_does_not_show_other_users_sessions(self, setup_db):
        async with _TestSessionFactory() as db:
            other_user = User(id="other-user-id", display_name="other", avatar_url="")
            db.add(other_user)
            await db.flush()
            await seed_session(db, session_id="sess-other", user_id="other-user-id")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/user/assessments")

        assert response.json() == []


class TestDeleteUserAssessment:
    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, setup_db):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/user/assessments/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_other_users_session_returns_403(self, setup_db):
        async with _TestSessionFactory() as db:
            other_user = User(id="other-user-id", display_name="other", avatar_url="")
            db.add(other_user)
            await db.flush()
            await seed_session(db, session_id="sess-other", user_id="other-user-id")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/user/assessments/sess-other")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_own_session_returns_204(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db, session_id="sess-del-1")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/user/assessments/sess-del-1")
        assert response.status_code == 204

        # Verify it's gone
        async with _TestSessionFactory() as db:
            row = await db.get(AssessmentSession, "sess-del-1")
            assert row is None

    @pytest.mark.asyncio
    async def test_delete_removes_associated_result(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db, session_id="sess-del-2", status="completed")
            await seed_result(db, session_id="sess-del-2")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/user/assessments/sess-del-2")
        assert response.status_code == 204

        async with _TestSessionFactory() as db:
            result = await db.execute(
                select(AssessmentResult).where(AssessmentResult.session_id == "sess-del-2")
            )
            assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_delete_removes_associated_materials(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db, session_id="sess-del-3")
            db.add(
                MaterialResult(
                    session_id="sess-del-3",
                    concept_id="react_hooks",
                    domain="frontend_engineering",
                    bloom_score=0.8,
                    quality_score=0.9,
                    iteration_count=1,
                    material={"content": "test"},
                )
            )
            await db.commit()

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.delete("/api/user/assessments/sess-del-3")
        assert response.status_code == 204

        async with _TestSessionFactory() as db:
            result = await db.execute(
                select(MaterialResult).where(MaterialResult.session_id == "sess-del-3")
            )
            assert result.scalar_one_or_none() is None
