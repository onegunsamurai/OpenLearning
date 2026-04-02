"""Assessment orchestration service.

Contains all business logic extracted from ``routes/assessment.py``.
Route handlers become thin HTTP wrappers that delegate here.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from langgraph.types import Command

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AssessmentResult, AssessmentSession
from app.deps import AuthUser
from app.exceptions import (
    AssessmentNotCompleteError,
    AssessmentValidationError,
    GraphInterruptError,
    SessionAlreadyCompletedError,
    SessionTimedOutError,
)
from app.graph.router import MAX_TOPICS
from app.graph.state import (
    THOROUGHNESS_CAPS,
    Thoroughness,
    make_initial_state,
)
from app.knowledge_base.loader import (
    get_all_topics,
    get_target_graph,
    get_target_graph_for_concepts,
    map_skills_to_domain,
)
from app.models.assessment_api import (
    AssessmentReportResponse,
    AssessmentStartRequest,
    AssessmentStartResponse,
    KnowledgeGraphOut,
)
from app.models.events import AssessmentEvent, CompleteEvent, ErrorEvent, QuestionEvent
from app.repositories import material_repo, result_repo, session_repo
from app.routes.export_utils import build_assessment_markdown
from app.services.ai import api_key_scope, classify_anthropic_error
from app.services.assessment_mappers import (
    build_gap_analysis_out,
    build_kg_out,
    build_learning_plan_out,
    build_proficiency_scores,
    build_report_from_db,
)

logger = logging.getLogger("openlearning.assessment")


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AssessmentReportResult:
    """Returned by ``get_assessment_report`` so the route knows whether to
    trigger the content pipeline."""

    report: AssessmentReportResponse
    first_completion: bool


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Returned by ``export_assessment`` so the route can build headers."""

    markdown: str
    session_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_interrupt(graph_state) -> dict | None:
    """Extract the first interrupt value from a LangGraph state snapshot.

    Returns ``None`` when no pending interrupt is found.
    """
    for task in graph_state.tasks or []:
        if hasattr(task, "interrupts") and task.interrupts:
            return task.interrupts[0].value
    return None


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def start_assessment(
    db: AsyncSession,
    graph: CompiledGraph,
    user: AuthUser,
    request: AssessmentStartRequest,
    api_key: str,
) -> AssessmentStartResponse:
    """Create a new assessment session and return the first question."""
    if not request.skill_ids:
        raise AssessmentValidationError("At least one skill is required")

    # Map skills to domain (skip mapping if role_id provided)
    domain = request.role_id if request.role_id else map_skills_to_domain(request.skill_ids)

    # Build target graph — filter to selected concepts when role_id is provided
    if request.role_id:
        target_graph = get_target_graph_for_concepts(
            domain, request.target_level, request.skill_ids
        )
    else:
        target_graph = get_target_graph(domain, request.target_level)

    # Create initial state
    session_id = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())

    db.add(
        AssessmentSession(
            session_id=session_id,
            thread_id=thread_id,
            skill_ids=request.skill_ids,
            target_level=request.target_level,
            role_id=request.role_id,
            status="active",
            user_id=user.user_id,
        )
    )
    await db.commit()

    initial_state = make_initial_state(
        candidate_id=session_id,
        skill_ids=request.skill_ids,
        skill_domain=domain,
        target_level=request.target_level,
        thoroughness=request.thoroughness,
    )
    initial_state["target_graph"] = target_graph

    # Run graph until first interrupt (calibration question 1)
    config = {"configurable": {"thread_id": thread_id}}

    with api_key_scope(api_key):
        await graph.ainvoke(initial_state, config)

    # The graph will be interrupted. Get the interrupt value.
    graph_state = await graph.aget_state(config)
    if not graph_state.tasks:
        raise GraphInterruptError("Pipeline did not produce a question")

    interrupt_data = extract_interrupt(graph_state)
    if not interrupt_data:
        raise GraphInterruptError("No interrupt data found")

    question_text = interrupt_data["question"]["text"]

    # Compute estimated questions from topic count and thoroughness
    topic_count = (
        len(request.skill_ids)
        if request.role_id
        else len(get_all_topics(domain, request.target_level))
    )
    per_topic = THOROUGHNESS_CAPS[Thoroughness(request.thoroughness)]
    estimated_questions = min(topic_count, MAX_TOPICS) * per_topic

    return AssessmentStartResponse(
        session_id=session_id,
        question=question_text,
        question_type=interrupt_data.get("type", "calibration"),
        step=interrupt_data.get("step", 1),
        total_steps=interrupt_data.get("total_steps", 3),
        estimated_questions=estimated_questions,
    )


async def respond_to_assessment(
    db: AsyncSession,
    graph: CompiledGraph,
    session_id: str,
    user: AuthUser,
    response: str,
    api_key: str,
) -> AsyncGenerator[AssessmentEvent, None]:
    """Validate the session eagerly, then return a lazy event generator.

    This is an ``async def`` that **returns** (not yields) an async generator.
    Validation (ownership, status, timestamp) runs eagerly so that domain
    exceptions are raised **before** ``StreamingResponse`` starts.
    The returned ``_assessment_event_stream`` generator is consumed by SSEAdapter.
    """
    # --- eager validation (runs before streaming starts) ---
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
    thread_id = session_row.thread_id
    if session_row.status == "timed_out":
        raise SessionTimedOutError("Session has timed out")
    if session_row.status == "completed":
        raise SessionAlreadyCompletedError("Session is already completed")
    session_row.updated_at = func.now()
    await db.commit()

    # --- return lazy generator for the streaming part ---
    return _assessment_event_stream(db, graph, session_id, thread_id, response, api_key)


async def _assessment_event_stream(
    db: AsyncSession,
    graph: CompiledGraph,
    session_id: str,
    thread_id: str,
    response: str,
    api_key: str,
) -> AsyncGenerator[AssessmentEvent, None]:
    """Yield domain events for the SSE stream (internal helper)."""
    config = {"configurable": {"thread_id": thread_id}}

    with api_key_scope(api_key):
        try:
            # Resume graph with user's answer
            await graph.ainvoke(Command(resume=response), config)

            # Check new state
            graph_state = await graph.aget_state(config)

            interrupt_data = extract_interrupt(graph_state)

            if interrupt_data:
                question_text = interrupt_data["question"]["text"]
                meta = {
                    "type": interrupt_data.get("type", "assessment"),
                    "step": interrupt_data.get("step"),
                    "total_steps": interrupt_data.get("total_steps"),
                    "topics_evaluated": interrupt_data.get("topics_evaluated"),
                    "total_questions": interrupt_data.get("total_questions"),
                    "max_questions": interrupt_data.get("max_questions"),
                }
                yield QuestionEvent(text=question_text, meta=meta)
            else:
                # Pipeline completed
                state_values = graph_state.values
                scores = build_proficiency_scores(state_values)
                yield CompleteEvent(scores=scores)
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.exception("Error in assessment stream", extra={"session_id": session_id})
            try:
                err_session = await session_repo.get_session(db, session_id)
                if err_session and err_session.status == "active":
                    err_session.status = "error"
                    await db.commit()
            except Exception:
                logger.exception(
                    "Failed to mark session as error", extra={"session_id": session_id}
                )
            result = classify_anthropic_error(exc)
            if result:
                status, detail, headers = result
                yield ErrorEvent(
                    status=status,
                    detail=detail,
                    retry_after=headers.get("Retry-After"),
                )
            else:
                yield ErrorEvent(status=500, detail="An internal error occurred")


async def get_assessment_graph(
    db: AsyncSession,
    graph: CompiledGraph,
    session_id: str,
    user: AuthUser,
) -> KnowledgeGraphOut:
    """Return the live knowledge graph from the graph checkpoint."""
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
    thread_id = session_row.thread_id

    config = {"configurable": {"thread_id": thread_id}}
    state = (await graph.aget_state(config)).values

    kg = state.get("knowledge_graph")
    return build_kg_out(kg)


async def get_assessment_report(
    db: AsyncSession,
    graph: CompiledGraph,
    session_id: str,
    user: AuthUser,
) -> AssessmentReportResult:
    """Build the assessment report, persisting the result on first completion.

    Returns an ``AssessmentReportResult`` so the route handler knows whether
    to trigger the content pipeline.
    """
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
    thread_id = session_row.thread_id

    # Try DB-stored result first (optimised for completed sessions)
    result_row = await result_repo.get_result_by_session(db, session_id)

    if result_row:
        report = build_report_from_db(result_row, session_row)
        return AssessmentReportResult(report=report, first_completion=False)

    # Fall back to live graph state for active sessions
    config = {"configurable": {"thread_id": thread_id}}
    state = (await graph.aget_state(config)).values

    kg = state.get("knowledge_graph")
    gap_nodes = state.get("gap_nodes", [])
    learning_plan = state.get("learning_plan")
    enriched = state.get("enriched_gap_analysis")

    # Guard: the pipeline runs analyze_gaps → enrich_gaps → generate_plan → END.
    if not state.get("assessment_complete", False) or enriched is None or not enriched.summary:
        raise AssessmentNotCompleteError(
            "Assessment not yet complete. Please finish the assessment first."
        )

    proficiency_scores = build_proficiency_scores(state)

    # Store result in DB and mark session completed — only for active sessions.
    first_completion = False
    if not result_row and session_row.status == "active":
        db.add(
            AssessmentResult(
                session_id=session_id,
                knowledge_graph=kg.model_dump() if kg else None,
                gap_nodes=[n.model_dump() for n in gap_nodes] if gap_nodes else None,
                learning_plan=learning_plan.model_dump() if learning_plan else None,
                proficiency_scores=[s.model_dump() for s in proficiency_scores],
                enriched_gap_analysis=enriched.model_dump() if enriched else None,
            )
        )
        session_row.status = "completed"
        await db.commit()
        first_completion = True

    report = AssessmentReportResponse(
        knowledge_graph=build_kg_out(kg),
        gap_analysis=build_gap_analysis_out(enriched),
        learning_plan=build_learning_plan_out(learning_plan),
        proficiency_scores=proficiency_scores,
    )
    return AssessmentReportResult(report=report, first_completion=first_completion)


async def export_assessment(
    db: AsyncSession,
    graph: CompiledGraph,
    session_id: str,
    user: AuthUser,
) -> ExportResult:
    """Export assessment results as markdown."""
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
    thread_id = session_row.thread_id

    # Try DB-stored result first
    result_row = await result_repo.get_result_by_session(db, session_id)

    if result_row:
        knowledge_graph = result_row.knowledge_graph
        gap_nodes = result_row.gap_nodes
        learning_plan = result_row.learning_plan
        proficiency_scores = result_row.proficiency_scores
        completed_at = result_row.completed_at
    else:
        # Fall back to live graph state
        config = {"configurable": {"thread_id": thread_id}}
        state = (await graph.aget_state(config)).values

        kg = state.get("knowledge_graph")
        gap_node_objs = state.get("gap_nodes", [])
        lp = state.get("learning_plan")
        scores = build_proficiency_scores(state)

        knowledge_graph = kg.model_dump() if kg else None
        gap_nodes = [n.model_dump() for n in gap_node_objs] if gap_node_objs else None
        learning_plan = lp.model_dump() if lp else None
        proficiency_scores = [s.model_dump() for s in scores]
        completed_at = None

    # Fetch materials for export (may be empty if pipeline hasn't run)
    material_rows = await material_repo.get_materials_by_session(db, session_id)
    materials_data = (
        [
            {
                "concept_id": row.concept_id,
                "material": row.material,
                "quality_score": row.quality_score,
                "bloom_score": row.bloom_score,
                "quality_flag": row.quality_flag,
            }
            for row in material_rows
        ]
        if material_rows
        else None
    )

    markdown = build_assessment_markdown(
        session_id=session_id,
        target_level=session_row.target_level,
        completed_at=completed_at,
        knowledge_graph=knowledge_graph,
        gap_nodes=gap_nodes,
        learning_plan=learning_plan,
        proficiency_scores=proficiency_scores,
        materials=materials_data,
    )

    return ExportResult(markdown=markdown, session_id=session_id)


async def resume_assessment(
    db: AsyncSession,
    graph: CompiledGraph,
    session_id: str,
    user: AuthUser,
) -> AssessmentStartResponse:
    """Resume an active assessment session by loading the pending interrupt."""
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
    if session_row.status == "timed_out":
        raise SessionTimedOutError("Session has timed out")
    if session_row.status == "completed":
        raise SessionAlreadyCompletedError("Session already completed")

    config = {"configurable": {"thread_id": session_row.thread_id}}
    graph_state = await graph.aget_state(config)

    interrupt_data = extract_interrupt(graph_state)
    if not interrupt_data:
        raise GraphInterruptError("No pending question found")

    question = interrupt_data.get("question")
    if not isinstance(question, dict) or "text" not in question:
        raise GraphInterruptError("Malformed interrupt data in checkpoint")

    return AssessmentStartResponse(
        session_id=session_id,
        question=question["text"],
        question_type=interrupt_data.get("type", "assessment"),
        step=interrupt_data.get("step", 1),
        total_steps=interrupt_data.get("total_steps", 3),
    )
