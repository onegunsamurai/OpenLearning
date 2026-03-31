from __future__ import annotations

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import PlainTextResponse, StreamingResponse

from app.agents.gap_analyzer import analyze_gaps
from app.agents.gap_enricher import _compute_overall_readiness, _compute_priority
from app.db import AssessmentResult, AssessmentSession, get_db
from app.deps import AuthUser, get_current_user, get_user_api_key
from app.graph.router import MAX_TOPICS
from app.graph.state import (
    THOROUGHNESS_CAPS,
    BloomLevel,
    KnowledgeGraph,
    KnowledgeNode,
    Thoroughness,
    make_initial_state,
)
from app.knowledge_base.loader import (
    get_all_topics,
    get_target_graph,
    get_target_graph_for_concepts,
    map_skills_to_domain,
)
from app.models.assessment import ProficiencyScore
from app.models.assessment_api import (
    AssessmentReportResponse,
    AssessmentRespondRequest,
    AssessmentStartRequest,
    AssessmentStartResponse,
    KnowledgeGraphOut,
    KnowledgeNodeOut,
    LearningPhaseOut,
    LearningPlanOut,
    ResourceOut,
)
from app.models.gap_analysis import GapAnalysis, GapItem
from app.repositories import result_repo, session_repo
from app.routes.export_utils import build_assessment_markdown
from app.services.ai import api_key_scope, classify_anthropic_error
from app.services.content_trigger import trigger_content_pipeline

logger = logging.getLogger("openlearning.assessment")

router = APIRouter()


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


@router.post("/assessment/{session_id}/respond")
async def assessment_respond(
    session_id: str,
    request: AssessmentRespondRequest,
    req: Request,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_user_api_key),
) -> StreamingResponse:
    # Touch updated_at to prevent session timeout during active assessments
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
    thread_id = session_row.thread_id
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
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
    thread_id = session_row.thread_id

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
    # Ownership check
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
    thread_id = session_row.thread_id

    # Try DB-stored result first (optimized for completed sessions)
    result_row = await result_repo.get_result_by_session(db, session_id)

    if result_row:
        return _build_report_from_db(result_row, session_row)

    # Fall back to live graph state for active sessions
    graph = req.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    state = (await graph.aget_state(config)).values

    kg = state.get("knowledge_graph")
    gap_nodes = state.get("gap_nodes", [])
    learning_plan = state.get("learning_plan")
    enriched = state.get("enriched_gap_analysis")

    # Guard: the pipeline runs analyze_gaps → enrich_gaps → generate_plan → END.
    # Both flags must be true: assessment_complete (set in analyze_gaps) AND
    # enriched gap analysis must have been produced (set in enrich_gaps).
    if not state.get("assessment_complete", False) or enriched is None or not enriched.summary:
        raise HTTPException(
            status_code=400,
            detail="Assessment not yet complete. Please finish the assessment first.",
        )

    proficiency_scores = _build_proficiency_scores(state)

    # Store result in DB and mark session completed — only for active sessions.
    # Errored or timed-out sessions must not be upgraded to "completed", and the
    # content pipeline must not be triggered for sessions that never finished.
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

        # Trigger content generation pipeline in background
        trigger_content_pipeline(session_id, req.app)

    return AssessmentReportResponse(
        knowledge_graph=_build_kg_out(kg),
        gap_analysis=_build_gap_analysis_out(enriched),
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
    # Fetch session row for metadata + ownership check
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
        target_level=session_row.target_level,
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
    _api_key: str = Depends(get_user_api_key),
) -> AssessmentStartResponse:
    """Resume an active assessment session by loading the pending interrupt."""
    session_row = await session_repo.get_session_with_ownership(db, session_id, user.user_id)
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

    question = interrupt_data.get("question")
    if not isinstance(question, dict) or "text" not in question:
        raise HTTPException(status_code=500, detail="Malformed interrupt data in checkpoint")

    return AssessmentStartResponse(
        session_id=session_id,
        question=question["text"],
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


def _build_gap_analysis_out(enriched) -> GapAnalysis:
    """Build GapAnalysis from state or DB data."""
    if not enriched:
        return GapAnalysis(overall_readiness=0, summary="", gaps=[])

    # Handle both Pydantic model and dict (from DB JSONB)
    if isinstance(enriched, dict):
        return GapAnalysis(
            overall_readiness=enriched.get("overall_readiness", 0),
            summary=enriched.get("summary", ""),
            gaps=[GapItem(**gap) for gap in enriched.get("gaps", [])],
        )

    return GapAnalysis(
        overall_readiness=enriched.overall_readiness,
        summary=enriched.summary,
        gaps=[
            GapItem(
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


def _reconstruct_kg(kg_data: dict | None) -> KnowledgeGraph:
    """Reconstruct a KnowledgeGraph from stored JSONB."""
    if not kg_data or "nodes" not in kg_data:
        return KnowledgeGraph()
    nodes: list[KnowledgeNode] = []
    for n in kg_data["nodes"]:
        try:
            bloom_level = BloomLevel(n.get("bloom_level", "remember"))
        except ValueError:
            bloom_level = BloomLevel.remember
        nodes.append(
            KnowledgeNode(
                concept=n.get("concept", ""),
                confidence=n.get("confidence", 0),
                bloom_level=bloom_level,
                prerequisites=n.get("prerequisites", []),
                evidence=n.get("evidence", []),
            )
        )
    return KnowledgeGraph(
        nodes=nodes,
        edges=[(src, dst) for src, dst in kg_data.get("edges", [])],
    )


def _recompute_gap_analysis(
    session_row: AssessmentSession,
    result_row: AssessmentResult,
) -> GapAnalysis:
    """Recompute gap analysis from stored knowledge graph and knowledge base.

    Re-runs the pure-Python gap detection against the current algorithm, then
    merges with existing LLM-generated enrichment data (recommendations and
    summary) so no LLM call is needed.
    """
    current_kg = _reconstruct_kg(result_row.knowledge_graph)
    stored_enriched = result_row.enriched_gap_analysis

    # Reconstruct target graph from session metadata
    role_id = session_row.role_id
    target_level = session_row.target_level
    skill_ids = session_row.skill_ids or []

    try:
        if role_id:
            domain = role_id
            target_kg = get_target_graph_for_concepts(domain, target_level, skill_ids)
        else:
            domain = map_skills_to_domain(skill_ids)
            target_kg = get_target_graph(domain, target_level)
    except (FileNotFoundError, ValueError):
        # Knowledge base no longer exists or level invalid — fall back to stored data
        return _build_gap_analysis_out(stored_enriched)

    # Re-run gap detection with the current algorithm (no tolerance threshold)
    state = {"knowledge_graph": current_kg, "target_graph": target_kg}
    gap_result = analyze_gaps(state)
    fresh_gap_nodes: list[KnowledgeNode] = gap_result["gap_nodes"]

    # Build lookup of existing enrichment items by skill_id
    existing_items: dict[str, dict] = {}
    if stored_enriched and "gaps" in stored_enriched:
        for item in stored_enriched["gaps"]:
            existing_items[item.get("skill_id", "")] = item

    # Merge: keep existing LLM recommendations, add new gaps with computed priority
    enriched_gaps: list[GapItem] = []
    for gap_node in fresh_gap_nodes:
        target_node = target_kg.get_node(gap_node.concept)
        target_conf = target_node.confidence if target_node else 0.0
        current_conf = gap_node.confidence

        # Always recompute numeric fields from current/target confidence so they
        # stay consistent with the freshly reconstructed knowledge graphs.
        current_level = int(current_conf * 100)
        target_level_pct = int(target_conf * 100)
        gap_value = max(target_level_pct - current_level, 0)
        priority_value = _compute_priority(current_conf, target_conf)

        existing = existing_items.get(gap_node.concept)
        if existing:
            # Preserve LLM-generated parts (skill_name, recommendation),
            # recompute numeric fields to avoid stale values.
            enriched_gaps.append(
                GapItem(
                    skill_id=gap_node.concept,
                    skill_name=existing.get("skill_name")
                    or gap_node.concept.replace("_", " ").title(),
                    current_level=current_level,
                    target_level=target_level_pct,
                    gap=gap_value,
                    priority=priority_value,
                    recommendation=existing.get("recommendation")
                    or "Continue developing this skill area to close the gap.",
                )
            )
        else:
            enriched_gaps.append(
                GapItem(
                    skill_id=gap_node.concept,
                    skill_name=gap_node.concept.replace("_", " ").title(),
                    current_level=current_level,
                    target_level=target_level_pct,
                    gap=gap_value,
                    priority=priority_value,
                    recommendation="Continue developing this skill area to close the gap.",
                )
            )

    # Sort by priority (critical first), then by gap size descending
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    enriched_gaps.sort(key=lambda g: (priority_order.get(g.priority, 4), -g.gap))

    # Recompute overall readiness from fresh data
    overall_readiness = _compute_overall_readiness(
        current_kg.nodes, target_kg.nodes, current_kg, target_kg
    )

    summary = stored_enriched.get("summary", "") if stored_enriched else ""

    return GapAnalysis(
        overall_readiness=overall_readiness,
        summary=summary,
        gaps=enriched_gaps,
    )


def _build_report_from_db(
    result_row: AssessmentResult,
    session_row: AssessmentSession,
) -> AssessmentReportResponse:
    """Build report response from a stored AssessmentResult row."""
    # Rebuild proficiency scores from stored JSONB
    proficiency_scores = [ProficiencyScore(**s) for s in (result_row.proficiency_scores or [])]

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

    # Recompute gap analysis from stored knowledge graph + knowledge base
    gap_analysis = _recompute_gap_analysis(session_row, result_row)

    return AssessmentReportResponse(
        knowledge_graph=kg_out,
        gap_analysis=gap_analysis,
        learning_plan=_build_learning_plan_out(result_row.learning_plan),
        proficiency_scores=proficiency_scores,
    )


def _build_proficiency_scores(state: dict) -> list[ProficiencyScore]:
    """Convert knowledge graph nodes to ProficiencyScore format for frontend compatibility."""
    kg = state.get("knowledge_graph")
    if not kg:
        return []

    scores = []
    for node in kg.nodes:
        scores.append(
            ProficiencyScore(
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
