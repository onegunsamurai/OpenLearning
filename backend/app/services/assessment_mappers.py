"""Pure data-transformation functions for assessment domain objects.

These mappers convert between graph state objects, DB JSONB dicts, and
API response models.  They contain **no I/O and no side effects**.
"""

from __future__ import annotations

import logging

from app.agents.gap_analyzer import analyze_gaps
from app.agents.gap_enricher import _compute_overall_readiness, _compute_priority
from app.db import AssessmentResult, AssessmentSession
from app.graph.state import BloomLevel, KnowledgeGraph, KnowledgeNode
from app.knowledge_base.loader import (
    get_target_graph,
    get_target_graph_for_concepts,
    map_skills_to_domain,
)
from app.models.assessment import ProficiencyScore
from app.models.assessment_api import (
    AssessmentReportResponse,
    KnowledgeGraphOut,
    KnowledgeNodeOut,
    LearningPhaseOut,
    LearningPlanOut,
    ResourceOut,
)
from app.models.gap_analysis import GapAnalysis, GapItem

logger = logging.getLogger("openlearning.assessment")


# ---------------------------------------------------------------------------
# DTO builders
# ---------------------------------------------------------------------------


def build_kg_out(kg) -> KnowledgeGraphOut:
    """Build ``KnowledgeGraphOut`` from a KnowledgeGraph state object."""
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


def build_gap_analysis_out(enriched) -> GapAnalysis:
    """Build ``GapAnalysis`` from state or DB data."""
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


def build_learning_plan_out(learning_plan) -> LearningPlanOut:
    """Build ``LearningPlanOut`` from state or DB data."""
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


def build_proficiency_scores(state: dict) -> list[ProficiencyScore]:
    """Convert knowledge graph nodes to ``ProficiencyScore`` list."""
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


# ---------------------------------------------------------------------------
# State reconstruction helpers
# ---------------------------------------------------------------------------


def reconstruct_kg(kg_data: dict | None) -> KnowledgeGraph:
    """Reconstruct a ``KnowledgeGraph`` from stored JSONB."""
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


def recompute_gap_analysis(
    session_row: AssessmentSession,
    result_row: AssessmentResult,
) -> GapAnalysis:
    """Recompute gap analysis from stored knowledge graph and knowledge base.

    Re-runs the pure-Python gap detection against the current algorithm, then
    merges with existing LLM-generated enrichment data (recommendations and
    summary) so no LLM call is needed.
    """
    current_kg = reconstruct_kg(result_row.knowledge_graph)
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
        return build_gap_analysis_out(stored_enriched)

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


def build_report_from_db(
    result_row: AssessmentResult,
    session_row: AssessmentSession,
) -> AssessmentReportResponse:
    """Build report response from a stored ``AssessmentResult`` row."""
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
    gap_analysis = recompute_gap_analysis(session_row, result_row)

    return AssessmentReportResponse(
        knowledge_graph=kg_out,
        gap_analysis=gap_analysis,
        learning_plan=build_learning_plan_out(result_row.learning_plan),
        proficiency_scores=proficiency_scores,
    )
