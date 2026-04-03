"""Tests for the assessment service layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.deps import AuthUser
from app.exceptions import (
    AssessmentNotCompleteError,
    GraphInterruptError,
    SessionAlreadyCompletedError,
    SessionTimedOutError,
)
from app.models.bloom import BloomLevel
from app.models.enriched_gap import EnrichedGapAnalysis
from app.models.events import CompleteEvent, ErrorEvent, QuestionEvent
from app.models.knowledge import KnowledgeGraph, KnowledgeNode
from app.models.pipeline_plan import LearningPhase, LearningPlan, Resource
from app.services.assessment_service import (
    extract_interrupt,
    get_assessment_report,
    respond_to_assessment,
    resume_assessment,
    start_assessment,
)

_user = AuthUser(user_id="u-1", display_name="Test", avatar_url="")


def _make_interrupt(text="What is React?"):
    return {
        "question": {"text": text},
        "type": "assessment",
        "topics_evaluated": 0,
        "total_questions": 0,
        "max_questions": 20,
    }


def _make_graph_state(interrupt_data=None, values=None):
    state = MagicMock()
    if interrupt_data is not None:
        task = MagicMock()
        task.interrupts = [MagicMock(value=interrupt_data)]
        state.tasks = [task]
    else:
        state.tasks = []
    state.values = values or {}
    return state


# ---------------------------------------------------------------------------
# extract_interrupt
# ---------------------------------------------------------------------------


class TestExtractInterrupt:
    def test_returns_interrupt_value(self):
        state = _make_graph_state(_make_interrupt())
        result = extract_interrupt(state)
        assert result["question"]["text"] == "What is React?"

    def test_returns_none_when_no_tasks(self):
        state = _make_graph_state()
        assert extract_interrupt(state) is None

    def test_returns_none_when_no_interrupts(self):
        state = MagicMock()
        task = MagicMock()
        task.interrupts = []
        state.tasks = [task]
        assert extract_interrupt(state) is None


# ---------------------------------------------------------------------------
# start_assessment
# ---------------------------------------------------------------------------


class TestStartAssessment:
    @pytest.mark.asyncio
    async def test_no_tasks_raises_graph_interrupt_error(self):
        db = AsyncMock()
        graph = AsyncMock()
        graph.ainvoke = AsyncMock(return_value=None)
        graph.aget_state = AsyncMock(return_value=_make_graph_state())  # no tasks

        request = MagicMock()
        request.skill_ids = ["react"]
        request.role_id = "frontend_engineering"
        request.target_level = "mid"
        request.thoroughness = "standard"

        with (
            patch(
                "app.services.assessment_service.get_target_graph_for_concepts",
                return_value=MagicMock(),
            ),
            pytest.raises(GraphInterruptError, match="did not produce a question"),
        ):
            await start_assessment(db, graph, _user, request, "sk-test")

    @pytest.mark.asyncio
    async def test_no_interrupt_data_raises_graph_interrupt_error(self):
        db = AsyncMock()
        graph = AsyncMock()
        graph.ainvoke = AsyncMock(return_value=None)
        task = MagicMock()
        task.interrupts = []
        state = MagicMock()
        state.tasks = [task]
        graph.aget_state = AsyncMock(return_value=state)

        request = MagicMock()
        request.skill_ids = ["react"]
        request.role_id = "frontend_engineering"
        request.target_level = "mid"
        request.thoroughness = "standard"

        with (
            patch(
                "app.services.assessment_service.get_target_graph_for_concepts",
                return_value=MagicMock(),
            ),
            pytest.raises(GraphInterruptError, match="No interrupt data"),
        ):
            await start_assessment(db, graph, _user, request, "sk-test")


# ---------------------------------------------------------------------------
# respond_to_assessment
# ---------------------------------------------------------------------------


class TestRespondToAssessment:
    @pytest.mark.asyncio
    async def test_timed_out_session_raises(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.thread_id = "t-1"
        session.status = "timed_out"

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            pytest.raises(SessionTimedOutError),
        ):
            await respond_to_assessment(db, graph, "s-1", _user, "answer", "sk-test")

    @pytest.mark.asyncio
    async def test_completed_session_raises(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.thread_id = "t-1"
        session.status = "completed"

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            pytest.raises(SessionAlreadyCompletedError),
        ):
            await respond_to_assessment(db, graph, "s-1", _user, "answer", "sk-test")

    @pytest.mark.asyncio
    async def test_yields_question_event_on_interrupt(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.thread_id = "t-1"
        session.status = "active"

        interrupt = _make_interrupt(text="Explain hooks.")
        graph.ainvoke = AsyncMock(return_value=None)
        graph.aget_state = AsyncMock(return_value=_make_graph_state(interrupt))

        with patch(
            "app.services.assessment_service.session_repo.get_session_with_ownership",
            new_callable=AsyncMock,
            return_value=session,
        ):
            gen = await respond_to_assessment(db, graph, "s-1", _user, "answer", "sk-test")
            events = [e async for e in gen]

        assert len(events) == 1
        assert isinstance(events[0], QuestionEvent)
        assert events[0].text == "Explain hooks."

    @pytest.mark.asyncio
    async def test_yields_complete_event_when_no_interrupt(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.thread_id = "t-1"
        session.status = "active"

        kg = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="react",
                    confidence=0.8,
                    bloom_level=BloomLevel.apply,
                    prerequisites=[],
                    evidence=["Good"],
                )
            ],
            edges=[],
        )
        state = _make_graph_state(interrupt_data=None, values={"knowledge_graph": kg})
        graph.ainvoke = AsyncMock(return_value=None)
        graph.aget_state = AsyncMock(return_value=state)

        with patch(
            "app.services.assessment_service.session_repo.get_session_with_ownership",
            new_callable=AsyncMock,
            return_value=session,
        ):
            gen = await respond_to_assessment(db, graph, "s-1", _user, "answer", "sk-test")
            events = [e async for e in gen]

        assert len(events) == 1
        assert isinstance(events[0], CompleteEvent)
        assert len(events[0].scores) == 1

    @pytest.mark.asyncio
    async def test_yields_error_event_on_graph_failure(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.thread_id = "t-1"
        session.status = "active"

        graph.ainvoke = AsyncMock(side_effect=RuntimeError("Graph exploded"))

        err_session = MagicMock()
        err_session.status = "active"

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            patch(
                "app.services.assessment_service.session_repo.get_session",
                new_callable=AsyncMock,
                return_value=err_session,
            ),
        ):
            gen = await respond_to_assessment(db, graph, "s-1", _user, "answer", "sk-test")
            events = [e async for e in gen]

        assert len(events) == 1
        assert isinstance(events[0], ErrorEvent)
        assert events[0].status == 500


# ---------------------------------------------------------------------------
# get_assessment_report
# ---------------------------------------------------------------------------


class TestGetAssessmentReport:
    @pytest.mark.asyncio
    async def test_raises_not_complete(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.thread_id = "t-1"

        state = MagicMock()
        state.values = {
            "knowledge_graph": MagicMock(),
            "assessment_complete": False,
            "enriched_gap_analysis": None,
        }
        graph.aget_state = AsyncMock(return_value=state)

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            patch(
                "app.services.assessment_service.result_repo.get_result_by_session",
                new_callable=AsyncMock,
                return_value=None,
            ),
            pytest.raises(AssessmentNotCompleteError),
        ):
            await get_assessment_report(db, graph, "s-1", _user)

    @pytest.mark.asyncio
    async def test_first_completion_flag(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.thread_id = "t-1"
        session.status = "active"

        kg = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="react",
                    confidence=0.8,
                    bloom_level=BloomLevel.apply,
                    prerequisites=[],
                    evidence=[],
                )
            ],
            edges=[],
        )
        enriched = EnrichedGapAnalysis(
            overall_readiness=80,
            summary="Good progress",
            gaps=[],
        )
        lp = LearningPlan(
            phases=[
                LearningPhase(
                    phase_number=1,
                    title="Foundation",
                    concepts=["React"],
                    rationale="Core",
                    resources=[Resource(type="doc", title="Docs")],
                    estimated_hours=5,
                )
            ],
            total_hours=5,
            summary="Learn React",
        )
        state = MagicMock()
        state.values = {
            "knowledge_graph": kg,
            "gap_nodes": [],
            "learning_plan": lp,
            "enriched_gap_analysis": enriched,
            "assessment_complete": True,
        }
        graph.aget_state = AsyncMock(return_value=state)

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            patch(
                "app.services.assessment_service.result_repo.get_result_by_session",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            result = await get_assessment_report(db, graph, "s-1", _user)

        assert result.first_completion is True
        assert result.report.knowledge_graph is not None

    @pytest.mark.asyncio
    async def test_cached_result_not_first_completion(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.thread_id = "t-1"
        session.role_id = None
        session.target_level = "mid"
        session.skill_ids = ["react"]

        result_row = MagicMock()
        result_row.knowledge_graph = {
            "nodes": [
                {
                    "concept": "react",
                    "confidence": 0.8,
                    "bloom_level": "apply",
                    "prerequisites": [],
                    "evidence": [],
                }
            ],
            "edges": [],
        }
        result_row.gap_nodes = []
        result_row.learning_plan = {"summary": "", "total_hours": 0, "phases": []}
        result_row.proficiency_scores = []
        result_row.enriched_gap_analysis = {
            "overall_readiness": 80,
            "summary": "Good",
            "gaps": [],
        }

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            patch(
                "app.services.assessment_service.result_repo.get_result_by_session",
                new_callable=AsyncMock,
                return_value=result_row,
            ),
            patch(
                "app.services.assessment_mappers.map_skills_to_domain",
                return_value="frontend_engineering",
            ),
            patch(
                "app.services.assessment_mappers.get_target_graph",
                return_value=KnowledgeGraph(),
            ),
        ):
            result = await get_assessment_report(db, graph, "s-1", _user)

        assert result.first_completion is False


# ---------------------------------------------------------------------------
# resume_assessment
# ---------------------------------------------------------------------------


class TestResumeAssessment:
    @pytest.mark.asyncio
    async def test_timed_out_raises(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.status = "timed_out"

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            pytest.raises(SessionTimedOutError),
        ):
            await resume_assessment(db, graph, "s-1", _user)

    @pytest.mark.asyncio
    async def test_completed_raises(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.status = "completed"

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            pytest.raises(SessionAlreadyCompletedError),
        ):
            await resume_assessment(db, graph, "s-1", _user)

    @pytest.mark.asyncio
    async def test_no_interrupt_raises_graph_error(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.status = "active"
        session.thread_id = "t-1"
        graph.aget_state = AsyncMock(return_value=_make_graph_state())

        with (
            patch(
                "app.services.assessment_service.session_repo.get_session_with_ownership",
                new_callable=AsyncMock,
                return_value=session,
            ),
            pytest.raises(GraphInterruptError, match="No pending question"),
        ):
            await resume_assessment(db, graph, "s-1", _user)

    @pytest.mark.asyncio
    async def test_returns_question_on_success(self):
        db = AsyncMock()
        graph = AsyncMock()
        session = MagicMock()
        session.status = "active"
        session.thread_id = "t-1"

        interrupt = _make_interrupt(text="What are hooks?")
        graph.aget_state = AsyncMock(return_value=_make_graph_state(interrupt))

        with patch(
            "app.services.assessment_service.session_repo.get_session_with_ownership",
            new_callable=AsyncMock,
            return_value=session,
        ):
            result = await resume_assessment(db, graph, "s-1", _user)

        assert result.question == "What are hooks?"
