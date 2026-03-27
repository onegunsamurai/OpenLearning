"""Tests for assessment routes (start, respond, graph, report)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import AssessmentResult, AssessmentSession, User
from app.graph.state import (
    BloomLevel,
    EnrichedGapAnalysis,
    KnowledgeGraph,
    KnowledgeNode,
    LearningPhase,
    LearningPlan,
    Resource,
)
from tests.conftest import _mock_graph, _test_app, _TestSessionFactory, seed_session


def _make_interrupt_data(
    question_text: str = "What is React?",
    q_type: str = "calibration",
    step: int = 1,
    total_steps: int = 3,
) -> dict:
    return {
        "question": {"text": question_text},
        "type": q_type,
        "step": step,
        "total_steps": total_steps,
    }


def _make_graph_state_with_interrupt(interrupt_data: dict | None = None) -> MagicMock:
    """Build a mock graph state with interrupt tasks."""
    state = MagicMock()
    if interrupt_data is not None:
        task = MagicMock()
        task.interrupts = [MagicMock(value=interrupt_data)]
        state.tasks = [task]
    else:
        state.tasks = []
    state.values = {}
    return state


def _make_kg() -> KnowledgeGraph:
    return KnowledgeGraph(
        nodes=[
            KnowledgeNode(
                concept="react_hooks",
                confidence=0.85,
                bloom_level=BloomLevel.apply,
                prerequisites=[],
                evidence=["Good understanding of useState"],
            ),
        ],
        edges=[],
    )


class TestAssessmentStart:
    @pytest.mark.asyncio
    async def test_start_empty_skills_returns_400(self, setup_db):
        with patch("app.routes.assessment.list_domains", return_value=["backend_engineering"]):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/start",
                    json={"skillIds": [], "targetLevel": "mid"},
                )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_start_unknown_role_returns_422(self, setup_db):
        with patch("app.routes.assessment.list_domains", return_value=["backend_engineering"]):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/start",
                    json={"skillIds": ["react"], "roleId": "nonexistent_role"},
                )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_start_success_returns_session_and_question(self, setup_db):
        interrupt = _make_interrupt_data()
        graph_state = _make_graph_state_with_interrupt(interrupt)

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        with (
            patch("app.routes.assessment.list_domains", return_value=["backend_engineering"]),
            patch("app.routes.assessment.map_skills_to_domain", return_value="backend_engineering"),
            patch("app.routes.assessment.get_target_graph", return_value=_make_kg()),
            patch("app.routes.assessment.get_all_topics", return_value=["t1", "t2"]),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/start",
                    json={"skillIds": ["react"], "targetLevel": "mid"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "sessionId" in data
        assert data["question"] == "What is React?"
        assert data["questionType"] == "calibration"
        _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_start_creates_db_session(self, setup_db):
        interrupt = _make_interrupt_data()
        graph_state = _make_graph_state_with_interrupt(interrupt)

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        with (
            patch("app.routes.assessment.list_domains", return_value=["backend_engineering"]),
            patch("app.routes.assessment.map_skills_to_domain", return_value="backend_engineering"),
            patch("app.routes.assessment.get_target_graph", return_value=_make_kg()),
            patch("app.routes.assessment.get_all_topics", return_value=["t1", "t2"]),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/start",
                    json={"skillIds": ["react"], "targetLevel": "mid"},
                )

        session_id = response.json()["sessionId"]
        async with _TestSessionFactory() as db:
            row = await db.get(AssessmentSession, session_id)
            assert row is not None
            assert row.status == "active"
        _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_start_uses_role_id_as_domain(self, setup_db):
        interrupt = _make_interrupt_data()
        graph_state = _make_graph_state_with_interrupt(interrupt)

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        with (
            patch("app.routes.assessment.list_domains", return_value=["frontend_engineering"]),
            patch(
                "app.routes.assessment.map_skills_to_domain", return_value="backend_engineering"
            ) as mock_map,
            patch(
                "app.routes.assessment.get_target_graph_for_concepts", return_value=_make_kg()
            ) as mock_tg,
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.post(
                    "/api/assessment/start",
                    json={
                        "skillIds": ["react"],
                        "roleId": "frontend_engineering",
                        "targetLevel": "mid",
                    },
                )

        mock_map.assert_not_called()
        mock_tg.assert_called_once_with("frontend_engineering", "mid", ["react"])
        _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_start_maps_skills_when_no_role_id(self, setup_db):
        interrupt = _make_interrupt_data()
        graph_state = _make_graph_state_with_interrupt(interrupt)

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        with (
            patch("app.routes.assessment.list_domains", return_value=["backend_engineering"]),
            patch(
                "app.routes.assessment.map_skills_to_domain", return_value="backend_engineering"
            ) as mock_map,
            patch("app.routes.assessment.get_target_graph", return_value=_make_kg()),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.post(
                    "/api/assessment/start",
                    json={"skillIds": ["react"], "targetLevel": "mid"},
                )

        mock_map.assert_called_once_with(["react"])
        _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_start_no_tasks_returns_500(self, setup_db):
        graph_state = MagicMock()
        graph_state.tasks = []

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        with (
            patch("app.routes.assessment.list_domains", return_value=["backend_engineering"]),
            patch("app.routes.assessment.map_skills_to_domain", return_value="backend_engineering"),
            patch("app.routes.assessment.get_target_graph", return_value=_make_kg()),
            patch("app.routes.assessment.get_all_topics", return_value=["t1", "t2"]),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/start",
                    json={"skillIds": ["react"], "targetLevel": "mid"},
                )

        assert response.status_code == 500
        _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_start_no_interrupt_data_returns_500(self, setup_db):
        task = MagicMock()
        task.interrupts = []
        graph_state = MagicMock()
        graph_state.tasks = [task]

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        with (
            patch("app.routes.assessment.list_domains", return_value=["backend_engineering"]),
            patch("app.routes.assessment.map_skills_to_domain", return_value="backend_engineering"),
            patch("app.routes.assessment.get_target_graph", return_value=_make_kg()),
            patch("app.routes.assessment.get_all_topics", return_value=["t1", "t2"]),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/start",
                    json={"skillIds": ["react"], "targetLevel": "mid"},
                )

        assert response.status_code == 500
        _mock_graph.reset_mock()


class TestAssessmentRespond:
    @pytest.mark.asyncio
    async def test_respond_session_not_found_returns_404(self, setup_db):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/assessment/nonexistent/respond", json={"response": "my answer"}
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_respond_timed_out_session_returns_410(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db, status="timed_out")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/assessment/sess-001/respond", json={"response": "my answer"}
            )
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_respond_returns_sse_with_next_question(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        interrupt = _make_interrupt_data(question_text="Explain hooks.", q_type="assessment")
        graph_state = _make_graph_state_with_interrupt(interrupt)

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/sess-001/respond", json={"response": "my answer"}
                )

            assert response.status_code == 200
            body = response.text
            assert "Explain hooks." in body
            assert "[META]" in body
            assert "[DONE]" in body
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_respond_assessment_complete(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        graph_state = MagicMock()
        graph_state.tasks = []
        graph_state.values = {"knowledge_graph": _make_kg()}

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/sess-001/respond", json={"response": "my answer"}
                )

            body = response.text
            assert "[ASSESSMENT_COMPLETE]" in body
            assert "[DONE]" in body
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_respond_meta_is_valid_json(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        interrupt = _make_interrupt_data()
        graph_state = _make_graph_state_with_interrupt(interrupt)

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/sess-001/respond", json={"response": "answer"}
                )

            for line in response.text.split("\n"):
                if "[META]" in line:
                    meta_json = line.split("[META]")[1].strip()
                    parsed = json.loads(meta_json)
                    assert "type" in parsed
                    break
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_respond_sse_content_type(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        interrupt = _make_interrupt_data()
        graph_state = _make_graph_state_with_interrupt(interrupt)

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/sess-001/respond", json={"response": "answer"}
                )

            assert "text/event-stream" in response.headers["content-type"]
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_respond_updates_session_timestamp(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        interrupt = _make_interrupt_data()
        graph_state = _make_graph_state_with_interrupt(interrupt)

        _mock_graph.ainvoke = AsyncMock(return_value=None)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.post("/api/assessment/sess-001/respond", json={"response": "answer"})

            async with _TestSessionFactory() as db:
                row = await db.get(AssessmentSession, "sess-001")
                assert row is not None
                assert row.updated_at is not None
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_respond_graph_error_yields_error_event(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        _mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("Graph exploded"))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/assessment/sess-001/respond", json={"response": "answer"}
                )

            assert "[ERROR]" in response.text
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_respond_graph_error_marks_session_as_error(self, setup_db):
        """A graph error during streaming must set session status to 'error', not leave it 'active'."""
        async with _TestSessionFactory() as db:
            await seed_session(db)

        _mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("Graph exploded"))

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.post("/api/assessment/sess-001/respond", json={"response": "answer"})

            async with _TestSessionFactory() as db:
                session_row = await db.get(AssessmentSession, "sess-001")
                assert session_row.status == "error"
        finally:
            _mock_graph.reset_mock()


class TestAssessmentGraph:
    @pytest.mark.asyncio
    async def test_graph_not_found_returns_404(self, setup_db):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/nonexistent/graph")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_graph_returns_nodes(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        graph_state = MagicMock()
        graph_state.values = {"knowledge_graph": _make_kg()}
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.get("/api/assessment/sess-001/graph")

            assert response.status_code == 200
            data = response.json()
            assert len(data["nodes"]) == 1
            assert data["nodes"][0]["concept"] == "react_hooks"
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_graph_no_kg_returns_empty_nodes(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        graph_state = MagicMock()
        graph_state.values = {}
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.get("/api/assessment/sess-001/graph")

            assert response.status_code == 200
            assert response.json()["nodes"] == []
        finally:
            _mock_graph.reset_mock()


class TestAssessmentReport:
    def _make_full_state_values(self) -> dict:
        kg = _make_kg()
        gap_nodes = [
            KnowledgeNode(
                concept="typescript_generics",
                confidence=0.3,
                bloom_level=BloomLevel.understand,
                prerequisites=["react_hooks"],
                evidence=[],
            )
        ]
        lp = LearningPlan(
            phases=[
                LearningPhase(
                    phase_number=1,
                    title="Foundation",
                    concepts=["TypeScript Generics"],
                    rationale="Biggest gap",
                    resources=[Resource(type="documentation", title="TS Docs")],
                    estimated_hours=10,
                )
            ],
            total_hours=10,
            summary="Learn TypeScript generics",
        )
        enriched = EnrichedGapAnalysis(
            overall_readiness=70,
            summary="Needs work on TypeScript generics",
            gaps=[],
        )
        return {
            "knowledge_graph": kg,
            "gap_nodes": gap_nodes,
            "enriched_gap_analysis": enriched,
            "learning_plan": lp,
        }

    @pytest.mark.asyncio
    async def test_report_not_found_returns_404(self, setup_db):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/nonexistent/report")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_report_returns_full_structure(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        graph_state = MagicMock()
        graph_state.values = self._make_full_state_values()
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.get("/api/assessment/sess-001/report")

            assert response.status_code == 200
            data = response.json()
            assert "knowledgeGraph" in data
            assert "gapAnalysis" in data
            assert "learningPlan" in data
            assert "proficiencyScores" in data
            assert len(data["knowledgeGraph"]["nodes"]) == 1
            assert data["gapAnalysis"]["overallReadiness"] == 70
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_report_creates_db_result(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        graph_state = MagicMock()
        graph_state.values = self._make_full_state_values()
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.get("/api/assessment/sess-001/report")

            async with _TestSessionFactory() as db:
                result = await db.execute(
                    select(AssessmentResult).where(AssessmentResult.session_id == "sess-001")
                )
                row = result.scalar_one_or_none()
                assert row is not None

                session_row = await db.get(AssessmentSession, "sess-001")
                assert session_row.status == "completed"
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_report_does_not_complete_errored_session(self, setup_db):
        """Fetching the report for an errored session must not store a result or change its status.

        Regression test for: failed sessions incorrectly marked as 'Completed' on dashboard.
        """
        async with _TestSessionFactory() as db:
            await seed_session(db, status="error")

        graph_state = MagicMock()
        graph_state.values = self._make_full_state_values()
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.get("/api/assessment/sess-001/report")

            async with _TestSessionFactory() as db:
                session_row = await db.get(AssessmentSession, "sess-001")
                assert session_row.status == "error", (
                    "Report endpoint must not mark an errored session as 'completed'"
                )
                # No AssessmentResult should be created for errored sessions —
                # that would cause a completedAt to appear on the dashboard card.
                result = await db.execute(
                    select(AssessmentResult).where(AssessmentResult.session_id == "sess-001")
                )
                assert result.scalar_one_or_none() is None, (
                    "Report endpoint must not persist a result row for an errored session"
                )
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_report_idempotent(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        graph_state = MagicMock()
        graph_state.values = self._make_full_state_values()
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                await client.get("/api/assessment/sess-001/report")
                await client.get("/api/assessment/sess-001/report")

            async with _TestSessionFactory() as db:
                result = await db.execute(
                    select(AssessmentResult).where(AssessmentResult.session_id == "sess-001")
                )
                rows = result.scalars().all()
                assert len(rows) == 1
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_report_no_learning_plan(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        graph_state = MagicMock()
        graph_state.values = {
            "knowledge_graph": _make_kg(),
            "gap_nodes": [],
            "learning_plan": None,
        }
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.get("/api/assessment/sess-001/report")

            data = response.json()
            assert data["learningPlan"]["phases"] == []
            assert data["learningPlan"]["summary"] == ""
        finally:
            _mock_graph.reset_mock()

    @pytest.mark.asyncio
    async def test_report_proficiency_scores_from_kg(self, setup_db):
        async with _TestSessionFactory() as db:
            await seed_session(db)

        graph_state = MagicMock()
        graph_state.values = self._make_full_state_values()
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.get("/api/assessment/sess-001/report")

            data = response.json()
            scores = data["proficiencyScores"]
            assert len(scores) == 1
            assert scores[0]["skillId"] == "react_hooks"
            assert scores[0]["score"] == 85  # 0.85 * 100
        finally:
            _mock_graph.reset_mock()


class TestAssessmentResume:
    """Tests for GET /api/assessment/{session_id}/resume."""

    async def _seed_session_with_user(
        self,
        db,
        session_id: str = "sess-resume-001",
        thread_id: str = "thread-resume-001",
        status: str = "active",
        user_id: str = "test-user-id",
    ) -> str:
        """Seed a session with user_id set (needed for resume ownership checks)."""
        session = AssessmentSession(
            session_id=session_id,
            thread_id=thread_id,
            skill_ids=["react"],
            target_level="mid",
            status=status,
            user_id=user_id,
        )
        db.add(session)
        await db.commit()
        return session_id

    @pytest.mark.asyncio
    async def test_resume_nonexistent_session_returns_404(self, setup_db):
        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/nonexistent/resume")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resume_different_user_returns_403(self, setup_db):
        async with _TestSessionFactory() as db:
            # Create a different user so FK constraint is satisfied
            other_user = User(id="other-user-id", display_name="other", avatar_url="")
            db.add(other_user)
            await db.flush()
            await self._seed_session_with_user(db, user_id="other-user-id")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/sess-resume-001/resume")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_resume_timed_out_session_returns_410(self, setup_db):
        async with _TestSessionFactory() as db:
            await self._seed_session_with_user(db, status="timed_out")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/sess-resume-001/resume")
        assert response.status_code == 410

    @pytest.mark.asyncio
    async def test_resume_completed_session_returns_409(self, setup_db):
        async with _TestSessionFactory() as db:
            await self._seed_session_with_user(db, status="completed")

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/sess-resume-001/resume")
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_resume_active_session_returns_question(self, setup_db):
        async with _TestSessionFactory() as db:
            await self._seed_session_with_user(db)

        interrupt = _make_interrupt_data(
            question_text="What are React hooks?",
            q_type="assessment",
            step=2,
            total_steps=5,
        )
        graph_state = _make_graph_state_with_interrupt(interrupt)
        _mock_graph.aget_state = AsyncMock(return_value=graph_state)

        try:
            async with AsyncClient(
                transport=ASGITransport(app=_test_app), base_url="http://test"
            ) as client:
                response = await client.get("/api/assessment/sess-resume-001/resume")

            assert response.status_code == 200
            data = response.json()
            assert data["sessionId"] == "sess-resume-001"
            assert data["question"] == "What are React hooks?"
            assert data["questionType"] == "assessment"
            assert data["step"] == 2
            assert data["totalSteps"] == 5
        finally:
            _mock_graph.reset_mock()


class TestOwnershipChecks:
    """Verify ownership checks on report, export, graph, and respond endpoints."""

    async def _seed_other_user_session(self, db) -> str:
        """Create a session owned by a different user."""
        other_user = User(id="other-owner-id", display_name="other", avatar_url="")
        db.add(other_user)
        await db.flush()
        session = AssessmentSession(
            session_id="sess-other-001",
            thread_id="thread-other-001",
            skill_ids=["react"],
            target_level="mid",
            status="active",
            user_id="other-owner-id",
        )
        db.add(session)
        await db.commit()
        return "sess-other-001"

    @pytest.mark.asyncio
    async def test_report_returns_403_for_wrong_user(self, setup_db):
        async with _TestSessionFactory() as db:
            await self._seed_other_user_session(db)

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/sess-other-001/report")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_export_returns_403_for_wrong_user(self, setup_db):
        async with _TestSessionFactory() as db:
            await self._seed_other_user_session(db)

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/sess-other-001/export")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_graph_returns_403_for_wrong_user(self, setup_db):
        async with _TestSessionFactory() as db:
            await self._seed_other_user_session(db)

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/assessment/sess-other-001/graph")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_respond_returns_403_for_wrong_user(self, setup_db):
        async with _TestSessionFactory() as db:
            await self._seed_other_user_session(db)

        async with AsyncClient(
            transport=ASGITransport(app=_test_app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/assessment/sess-other-001/respond",
                json={"response": "my answer"},
            )
        assert response.status_code == 403
