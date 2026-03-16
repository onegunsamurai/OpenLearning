from __future__ import annotations

import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from pydantic import field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import PlainTextResponse, StreamingResponse

from app.db import AssessmentResult, AssessmentSession, get_db
from app.graph.state import make_initial_state
from app.knowledge_base.loader import get_target_graph, list_domains, map_skills_to_domain
from app.models.base import CamelModel
from app.routes.export_utils import build_assessment_markdown

logger = logging.getLogger("openlearning.assessment")

router = APIRouter()


class AssessmentStartRequest(CamelModel):
    skill_ids: list[str]
    target_level: str = "mid"
    role_id: str | None = None

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


class AssessmentReportResponse(CamelModel):
    knowledge_graph: KnowledgeGraphOut
    gap_nodes: list[GapNodeOut]
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
    request: AssessmentStartRequest, req: Request, db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    thread_id = await _get_thread_id(session_id, db)

    # Touch updated_at to prevent session timeout during active assessments
    session_row = await db.get(AssessmentSession, session_id)
    if session_row:
        if session_row.status == "timed_out":
            raise HTTPException(status_code=410, detail="Session has timed out")
        session_row.updated_at = func.now()
        await db.commit()

    graph = req.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    async def event_stream():
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
                import json

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
                import json

                scores_json = json.dumps({"scores": [s.model_dump(by_alias=True) for s in scores]})
                yield f"data: ```json\n{scores_json}\n```\n\n"

            yield "data: [DONE]\n\n"
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Error in assessment SSE stream", extra={"session_id": session_id})
            yield "data: [ERROR] An internal error occurred\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get(
    "/assessment/{session_id}/graph", response_model=KnowledgeGraphOut, response_model_by_alias=True
)
async def assessment_graph(
    session_id: str, req: Request, db: AsyncSession = Depends(get_db)
) -> KnowledgeGraphOut:
    thread_id = await _get_thread_id(session_id, db)

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
    session_id: str, req: Request, db: AsyncSession = Depends(get_db)
) -> AssessmentReportResponse:
    thread_id = await _get_thread_id(session_id, db)

    graph = req.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = (await graph.aget_state(config)).values

    kg = state.get("knowledge_graph")
    gap_nodes = state.get("gap_nodes", [])
    learning_plan = state.get("learning_plan")
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
            )
        )
        session_row = await db.get(AssessmentSession, session_id)
        if session_row:
            session_row.status = "completed"
        await db.commit()

    return AssessmentReportResponse(
        knowledge_graph=KnowledgeGraphOut(
            nodes=[
                KnowledgeNodeOut(
                    concept=n.concept,
                    confidence=n.confidence,
                    bloom_level=n.bloom_level.value,
                    prerequisites=n.prerequisites,
                )
                for n in (kg.nodes if kg else [])
            ]
        ),
        gap_nodes=[
            GapNodeOut(
                concept=n.concept,
                current_confidence=n.confidence,
                target_bloom_level=n.bloom_level.value,
                prerequisites=n.prerequisites,
            )
            for n in gap_nodes
        ],
        learning_plan=LearningPlanOut(
            summary=learning_plan.summary if learning_plan else "",
            total_hours=learning_plan.total_hours if learning_plan else 0,
            phases=[
                LearningPhaseOut(
                    phase_number=p.phase_number,
                    title=p.title,
                    concepts=p.concepts,
                    rationale=p.rationale,
                    resources=[
                        ResourceOut(type=r.type, title=r.title, url=r.url) for r in p.resources
                    ],
                    estimated_hours=p.estimated_hours,
                )
                for p in (learning_plan.phases if learning_plan else [])
            ],
        ),
        proficiency_scores=proficiency_scores,
    )


@router.get("/assessment/{session_id}/export")
async def assessment_export(
    session_id: str, req: Request, db: AsyncSession = Depends(get_db)
) -> PlainTextResponse:
    thread_id = await _get_thread_id(session_id, db)

    # Fetch session row for metadata
    session_row = await db.get(AssessmentSession, session_id)

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
