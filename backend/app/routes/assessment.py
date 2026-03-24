from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from pydantic import field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import PlainTextResponse, StreamingResponse

from app.db import AssessmentResult, AssessmentSession, get_db
from app.deps import AuthUser, get_current_user, get_user_api_key
from app.graph.state import make_initial_state
from app.knowledge_base.loader import get_target_graph, list_domains, map_skills_to_domain
from app.models.base import CamelModel
from app.routes.export_utils import build_assessment_markdown
from app.services.ai import api_key_scope, classify_anthropic_error
from app.services.content_trigger import trigger_content_pipeline

logger = logging.getLogger("openlearning.assessment")

router = APIRouter()


class AssessmentStartRequest(CamelModel):
    skill_ids: list[str]
    target_level: str = "mid"
    role_id: str | None = None

    @field_validator("skill_ids")
    @classmethod
    def validate_skill_ids(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ValueError("Too many skills (max 50)")
        return v

    @field_validator("role_id")
    @classmethod
    def validate_role_id(cls, v: str | None) -> str | None:
        if v is not None and v not in list_domains():
            raise ValueError(f"Unknown role: {v}")
        return v


class AssessmentStartResponse(CamelModel):
    session_id: str
    question: str
    question_type: str = "calibration"
    step: int = 1
    total_steps: int = 3


class AssessmentRespondRequest(CamelModel):
    response: str

    @field_validator("response")
    @classmethod
    def validate_response_length(cls, v: str) -> str:
        if len(v) > 10_000:
            raise ValueError("Response too long (max 10,000 characters)")
        return v


class KnowledgeNodeOut(CamelModel):
    concept: str
    confidence: float
    bloom_level: str
    prerequisites: list[str]


class KnowledgeGraphOut(CamelModel):
    nodes: list[KnowledgeNodeOut]


class ProficiencyScoreOut(CamelModel):
    skill_id: str
    skill_name: str
    score: int
    confidence: float
    reasoning: str


class ResourceOut(CamelModel):
    type: str
    title: str
    url: str | None = None


class LearningPhaseOut(CamelModel):
    phase_number: int
    title: str
    concepts: list[str]
    rationale: str
    resources: list[ResourceOut]
    estimated_hours: float


class LearningPlanOut(CamelModel):
    summary: str
    total_hours: float
    phases: list[LearningPhaseOut]


class GapNodeOut(CamelModel):
    concept: str
    current_confidence: float
    target_bloom_level: str
    prerequisites: list[str]


class EnrichedGapItemOut(CamelModel):
    skill_id: str
    skill_name: str
    current_level: int
    target_level: int
    gap: int
    priority: Literal["critical", "high", "medium", "low"]
    recommendation: str


class EnrichedGapAnalysisOut(CamelModel):
    overall_readiness: int
    summary: str
    gaps: list[EnrichedGapItemOut]


class AssessmentReportResponse(CamelModel):
    knowledge_graph: KnowledgeGraphOut
    gap_analysis: EnrichedGapAnalysisOut
    learning_plan: LearningPlanOut
    proficiency_scores: list[ProficiencyScoreOut]


async def _get_thread_id(session_id: str, db: AsyncSession) -> str:
    """Look up thread_id for a session, or raise 404."""
    result = await db.execute(
        select(AssessmentSession.thread_id).where(AssessmentSession.session_id == session_id)
    )
    thread_id = result.scalar_one_or_none()
    if not thread_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return thread_id


@router.post(
    "/assessment/start", response_model=AssessmentStartResponse, response_model_by_alias=True
)
async def assessment_start(
    request: AssessmentStartRequest,
    req: Request,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_user_api_key),
) -> AssessmentStartResponse:
    if not request.skill_ids:
        raise HTTPException(status_code=400, detail="At least one skill is required")

    # Map skills to domain (skip mapping if role_id provided)
    domain = request.role_id if request.role_id else map_skills_to_domain(request.skill_ids)

    # Build target graph
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
    )
    initial_state["target_graph"] = target_graph

    # Run graph until first interrupt (calibration question 1)
    graph = req.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    with api_key_scope(api_key):
        await graph.ainvoke(initial_state, config)

    # The graph will be interrupted. Get the interrupt value.
    graph_state = await graph.aget_state(config)
    if not graph_state.tasks:
        raise HTTPException(status_code=500, detail="Pipeline did not produce a question")

    # Extract interrupt data from the first task
    interrupt_data = None
    for task in graph_state.tasks:
        if hasattr(task, "interrupts") and task.interrupts:
            interrupt_data = task.interrupts[0].value
            break

    if not interrupt_data:
        raise HTTPException(status_code=500, detail="No interrupt data found")

    question_text = interrupt_data["question"]["text"]

    return AssessmentStartResponse(
        session_id=session_id,
        question=question_text,
        question_type=interrupt_data.get("type", "calibration"),
        step=interrupt_data.get("step", 1),
        total_steps=interrupt_data.get("total_steps", 3),
    )


@router.post("/assessment/{session_id}/respond")
async def assessment_respond(
    session_id: str,
    request: AssessmentRespondRequest,
    req: Request,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_user_api_key),
) -> StreamingResponse:
    thread_id = await _get_thread_id(session_id, db)

    # Touch updated_at to prevent session timeout during active assessments
    session_row = await db.get(AssessmentSession, session_id)
    if session_row:
        if session_row.user_id != user.user_id:
            raise HTTPException(status_code=403, detail="Not your session")
        if session_row.status == "timed_out":
            raise HTTPException(status_code=410, detail="Session has timed out")
        session_row.updated_at = func.now()
        await db.commit()

    graph = req.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    async def event_stream():
        with api_key_scope(api_key):
            try:
                # Resume graph with user's answer
                await graph.ainvoke(Command(resume=request.response), config)

                # Check new state
                graph_state = await graph.aget_state(config)

                # Check if pipeline completed (no more interrupts)
                has_interrupt = False
                interrupt_data = None
                for task in graph_state.tasks or []:
                    if hasattr(task, "interrupts") and task.interrupts:
                        has_interrupt = True
                        interrupt_data = task.interrupts[0].value
                        break

                if has_interrupt and interrupt_data:
                    question_text = interrupt_data["question"]["text"]
                    # Stream the question text
                    yield f"data: {question_text}\n\n"

                    # Send metadata
                    meta = {
                        "type": interrupt_data.get("type", "assessment"),
                        "step": interrupt_data.get("step"),
                        "total_steps": interrupt_data.get("total_steps"),
                        "topics_evaluated": interrupt_data.get("topics_evaluated"),
                        "total_questions": interrupt_data.get("total_questions"),
                        "max_questions": interrupt_data.get("max_questions"),
                    }
                    yield f"data: [META]{json.dumps(meta)}\n\n"
                else:
                    # Pipeline completed — send completion marker
                    yield "data: [ASSESSMENT_COMPLETE]\n\n"

                    # Build and send scores
                    state_values = graph_state.values
                    scores = _build_proficiency_scores(state_values)
                    scores_json = json.dumps(
                        {"scores": [s.model_dump(by_alias=True) for s in scores]}
                    )
                    yield f"data: ```json\n{scores_json}\n```\n\n"

                yield "data: [DONE]\n\n"
            except asyncio.CancelledError:
                return
            except Exception as exc:
                logger.exception("Error in assessment SSE stream", extra={"session_id": session_id})
                result = classify_anthropic_error(exc)
                if result:
                    status, detail, headers = result
                    error_payload = json.dumps(
                        {
                            "status": status,
                            "detail": detail,
                            "retryAfter": headers.get("Retry-After"),
                        }
                    )
                else:
                    error_payload = json.dumps(
                        {"status": 500, "detail": "An internal error occurred"}
                    )
                yield f"data: [ERROR]{error_payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get(
    "/assessment/{session_id}/graph", response_model=KnowledgeGraphOut, response_model_by_alias=True
)
async def assessment_graph(
    session_id: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> KnowledgeGraphOut:
    thread_id = await _get_thread_id(session_id, db)

    session_row = await db.get(AssessmentSession, session_id)
    if session_row and session_row.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not your session")

    graph = req.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = (await graph.aget_state(config)).values

    kg = state.get("knowledge_graph")
    if not kg:
        return KnowledgeGraphOut(nodes=[])

    return KnowledgeGraphOut(
        nodes=[
            KnowledgeNodeOut(
                concept=n.concept,
                confidence=n.confidence,
                bloom_level=n.bloom_level.value,
                prerequisites=n.prerequisites,
            )
            for n in kg.nodes
        ]
    )


@router.get(
    "/assessment/{session_id}/report",
    response_model=AssessmentReportResponse,
    response_model_by_alias=True,
)
async def assessment_report(
    session_id: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> AssessmentReportResponse:
    thread_id = await _get_thread_id(session_id, db)

    # Ownership check
    session_row = await db.get(AssessmentSession, session_id)
    if session_row and session_row.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not your session")

    # Try DB-stored result first (optimized for completed sessions)
    result_row_res = await db.execute(
        select(AssessmentResult).where(AssessmentResult.session_id == session_id)
    )
    result_row = result_row_res.scalar_one_or_none()

    if result_row:
        return _build_report_from_db(result_row)

    # Fall back to live graph state for active sessions
    graph = req.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = (await graph.aget_state(config)).values

    kg = state.get("knowledge_graph")
    gap_nodes = state.get("gap_nodes", [])
    learning_plan = state.get("learning_plan")
    enriched = state.get("enriched_gap_analysis")
    proficiency_scores = _build_proficiency_scores(state)

    # Store result in DB and mark session completed (idempotent)
    existing = await db.execute(
        select(AssessmentResult).where(AssessmentResult.session_id == session_id)
    )
    if not existing.scalar_one_or_none():
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
        if session_row:
            session_row.status = "completed"
        await db.commit()

        # Trigger content generation pipeline in background
        trigger_content_pipeline(session_id, req.app)

    return AssessmentReportResponse(
        knowledge_graph=_build_kg_out(kg),
        gap_analysis=_build_enriched_gap_out(enriched),
        learning_plan=_build_learning_plan_out(learning_plan),
        proficiency_scores=proficiency_scores,
    )


@router.get("/assessment/{session_id}/export")
async def assessment_export(
    session_id: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> PlainTextResponse:
    thread_id = await _get_thread_id(session_id, db)

    # Fetch session row for metadata + ownership check
    session_row = await db.get(AssessmentSession, session_id)
    if session_row and session_row.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not your session")

    # Try DB-stored result first
    result_row_res = await db.execute(
        select(AssessmentResult).where(AssessmentResult.session_id == session_id)
    )
    result_row = result_row_res.scalar_one_or_none()

    if result_row:
        knowledge_graph = result_row.knowledge_graph
        gap_nodes = result_row.gap_nodes
        learning_plan = result_row.learning_plan
        proficiency_scores = result_row.proficiency_scores
        completed_at = result_row.completed_at
    else:
        # Fall back to live graph state
        graph = req.app.state.graph
        config = {"configurable": {"thread_id": thread_id}}
        state = (await graph.aget_state(config)).values

        kg = state.get("knowledge_graph")
        gap_node_objs = state.get("gap_nodes", [])
        lp = state.get("learning_plan")
        scores = _build_proficiency_scores(state)

        knowledge_graph = kg.model_dump() if kg else None
        gap_nodes = [n.model_dump() for n in gap_node_objs] if gap_node_objs else None
        learning_plan = lp.model_dump() if lp else None
        proficiency_scores = [s.model_dump() for s in scores]
        completed_at = None

    markdown = build_assessment_markdown(
        session_id=session_id,
        target_level=session_row.target_level if session_row else "unknown",
        completed_at=completed_at,
        knowledge_graph=knowledge_graph,
        gap_nodes=gap_nodes,
        learning_plan=learning_plan,
        proficiency_scores=proficiency_scores,
    )

    return PlainTextResponse(
        content=markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="assessment-{session_id[:8]}.md"',
        },
    )


@router.get(
    "/assessment/{session_id}/resume",
    response_model=AssessmentStartResponse,
    response_model_by_alias=True,
)
async def assessment_resume(
    session_id: str,
    req: Request,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_user_api_key),
) -> AssessmentStartResponse:
    """Resume an active assessment session by loading the pending interrupt."""
    session_row = await db.get(AssessmentSession, session_id)
    if not session_row:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_row.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session_row.status == "timed_out":
        raise HTTPException(status_code=410, detail="Session has timed out")
    if session_row.status == "completed":
        raise HTTPException(status_code=409, detail="Session already completed")

    graph = req.app.state.graph
    config = {"configurable": {"thread_id": session_row.thread_id}}

    graph_state = await graph.aget_state(config)

    interrupt_data = None
    for task in graph_state.tasks or []:
        if hasattr(task, "interrupts") and task.interrupts:
            interrupt_data = task.interrupts[0].value
            break

    if not interrupt_data:
        raise HTTPException(status_code=409, detail="No pending question found")

    question_text = interrupt_data["question"]["text"]

    return AssessmentStartResponse(
        session_id=session_id,
        question=question_text,
        question_type=interrupt_data.get("type", "assessment"),
        step=interrupt_data.get("step", 1),
        total_steps=interrupt_data.get("total_steps", 3),
    )


# --- Helper functions ---


def _build_kg_out(kg) -> KnowledgeGraphOut:
    """Build KnowledgeGraphOut from a KnowledgeGraph state object."""
    if not kg:
        return KnowledgeGraphOut(nodes=[])
    return KnowledgeGraphOut(
        nodes=[
            KnowledgeNodeOut(
                concept=n.concept,
                confidence=n.confidence,
                bloom_level=n.bloom_level.value
                if hasattr(n.bloom_level, "value")
                else n.bloom_level,
                prerequisites=n.prerequisites,
            )
            for n in (kg.nodes if hasattr(kg, "nodes") else [])
        ]
    )


def _build_enriched_gap_out(enriched) -> EnrichedGapAnalysisOut:
    """Build EnrichedGapAnalysisOut from state or DB data."""
    if not enriched:
        return EnrichedGapAnalysisOut(overall_readiness=0, summary="", gaps=[])

    # Handle both Pydantic model and dict (from DB JSONB)
    if isinstance(enriched, dict):
        return EnrichedGapAnalysisOut(
            overall_readiness=enriched.get("overall_readiness", 0),
            summary=enriched.get("summary", ""),
            gaps=[EnrichedGapItemOut(**gap) for gap in enriched.get("gaps", [])],
        )

    return EnrichedGapAnalysisOut(
        overall_readiness=enriched.overall_readiness,
        summary=enriched.summary,
        gaps=[
            EnrichedGapItemOut(
                skill_id=g.skill_id,
                skill_name=g.skill_name,
                current_level=g.current_level,
                target_level=g.target_level,
                gap=g.gap,
                priority=g.priority,
                recommendation=g.recommendation,
            )
            for g in enriched.gaps
        ],
    )


def _build_learning_plan_out(learning_plan) -> LearningPlanOut:
    """Build LearningPlanOut from state or DB data."""
    if not learning_plan:
        return LearningPlanOut(summary="", total_hours=0, phases=[])

    # Handle dict (from DB JSONB)
    if isinstance(learning_plan, dict):
        return LearningPlanOut(
            summary=learning_plan.get("summary", ""),
            total_hours=learning_plan.get("total_hours", 0),
            phases=[
                LearningPhaseOut(
                    phase_number=p.get("phase_number", 0),
                    title=p.get("title", ""),
                    concepts=p.get("concepts", []),
                    rationale=p.get("rationale", ""),
                    resources=[
                        ResourceOut(
                            type=r.get("type", ""), title=r.get("title", ""), url=r.get("url")
                        )
                        for r in p.get("resources", [])
                    ],
                    estimated_hours=p.get("estimated_hours", 0),
                )
                for p in learning_plan.get("phases", [])
            ],
        )

    return LearningPlanOut(
        summary=learning_plan.summary,
        total_hours=learning_plan.total_hours,
        phases=[
            LearningPhaseOut(
                phase_number=p.phase_number,
                title=p.title,
                concepts=p.concepts,
                rationale=p.rationale,
                resources=[ResourceOut(type=r.type, title=r.title, url=r.url) for r in p.resources],
                estimated_hours=p.estimated_hours,
            )
            for p in learning_plan.phases
        ],
    )


def _build_report_from_db(result_row: AssessmentResult) -> AssessmentReportResponse:
    """Build report response from a stored AssessmentResult row."""
    # Rebuild proficiency scores from stored JSONB
    proficiency_scores = [ProficiencyScoreOut(**s) for s in (result_row.proficiency_scores or [])]

    # Rebuild knowledge graph from stored JSONB
    kg_data = result_row.knowledge_graph
    kg_out = KnowledgeGraphOut(nodes=[])
    if kg_data and "nodes" in kg_data:
        kg_out = KnowledgeGraphOut(
            nodes=[
                KnowledgeNodeOut(
                    concept=n.get("concept", ""),
                    confidence=n.get("confidence", 0),
                    bloom_level=n.get("bloom_level", "remember"),
                    prerequisites=n.get("prerequisites", []),
                )
                for n in kg_data["nodes"]
            ]
        )

    return AssessmentReportResponse(
        knowledge_graph=kg_out,
        gap_analysis=_build_enriched_gap_out(result_row.enriched_gap_analysis),
        learning_plan=_build_learning_plan_out(result_row.learning_plan),
        proficiency_scores=proficiency_scores,
    )


def _build_proficiency_scores(state: dict) -> list[ProficiencyScoreOut]:
    """Convert knowledge graph nodes to ProficiencyScore format for frontend compatibility."""
    kg = state.get("knowledge_graph")
    if not kg:
        return []

    scores = []
    for node in kg.nodes:
        scores.append(
            ProficiencyScoreOut(
                skill_id=node.concept,
                skill_name=node.concept.replace("_", " ").title(),
                score=int(node.confidence * 100),
                confidence=node.confidence,
                reasoning="; ".join(node.evidence[:3])
                if node.evidence
                else "Assessed during evaluation",
            )
        )
    return scores
