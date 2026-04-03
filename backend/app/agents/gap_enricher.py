from __future__ import annotations

from typing import Literal

from app.agents.gap_analyzer import get_effective_confidence
from app.agents.schemas import GapEnrichmentOutput
from app.graph.state import (
    AssessmentState,
    EnrichedGapAnalysis,
    EnrichedGapItem,
    KnowledgeGraph,
    KnowledgeNode,
)
from app.prompts.gap_enricher import GAP_ENRICHMENT_PROMPT_FOOTER, GAP_ENRICHMENT_PROMPT_HEADER
from app.services.ai import ainvoke_structured


def _compute_priority(
    current_confidence: float, target_confidence: float
) -> Literal["critical", "high", "medium", "low"]:
    """Derive priority from the confidence gap between current and target."""
    gap = target_confidence - current_confidence
    if gap > 0.6:
        return "critical"
    if gap > 0.4:
        return "high"
    if gap > 0.2:
        return "medium"
    return "low"


def _compute_overall_readiness(
    current_nodes: list[KnowledgeNode],
    target_nodes: list[KnowledgeNode],
    current_kg: KnowledgeGraph | None = None,
    target_kg: KnowledgeGraph | None = None,
) -> int:
    """Weighted average of (current_confidence / target_confidence) * 100.

    When knowledge graphs are provided, un-assessed concepts use inferred
    confidence from their assessed prerequisites instead of defaulting to 0.
    """
    if not target_nodes:
        return 100

    total_ratio = 0.0
    count = 0

    for target_node in target_nodes:
        current = next((n for n in current_nodes if n.concept == target_node.concept), None)
        if current:
            current_conf = current.confidence
        elif current_kg and target_kg:
            current_conf = get_effective_confidence(target_node.concept, current_kg, target_kg)
        else:
            current_conf = 0.0
        target_conf = target_node.confidence
        if target_conf > 0:
            total_ratio += min(current_conf / target_conf, 1.0)
            count += 1

    if count == 0:
        return 0
    return int((total_ratio / count) * 100)


async def enrich_gaps(state: AssessmentState) -> dict:
    """Enrich raw gap nodes with priority, readiness, and LLM-generated recommendations."""
    gap_nodes: list[KnowledgeNode] = state.get("gap_nodes", [])
    knowledge_graph = state.get("knowledge_graph")
    target_graph = state.get("target_graph")

    if not gap_nodes:
        return {
            "enriched_gap_analysis": EnrichedGapAnalysis(
                overall_readiness=100,
                summary="No significant gaps identified. Great job!",
                gaps=[],
            )
        }

    current_nodes = knowledge_graph.nodes if knowledge_graph else []
    target_nodes = target_graph.nodes if target_graph else []

    overall_readiness = _compute_overall_readiness(
        current_nodes, target_nodes, knowledge_graph, target_graph
    )

    # Build target confidence lookup
    target_map = {n.concept: n.confidence for n in target_nodes}

    # Build enriched items with computed fields
    enriched_items: list[EnrichedGapItem] = []
    for node in gap_nodes:
        target_conf = target_map.get(node.concept, 0.8)
        current_level = int(node.confidence * 100)
        target_level = int(target_conf * 100)
        enriched_items.append(
            EnrichedGapItem(
                skill_id=node.concept,
                skill_name=node.concept.replace("_", " ").title(),
                current_level=current_level,
                target_level=target_level,
                gap=max(target_level - current_level, 0),
                priority=_compute_priority(node.confidence, target_conf),
                recommendation="",  # filled by LLM below
            )
        )

    # Call LLM for summary + per-gap recommendations
    gap_summary = "\n".join(
        f"- {node.concept} (current confidence: {node.confidence:.1f}, "
        f"target bloom: {node.bloom_level.value}, "
        f"prerequisites: {', '.join(node.prerequisites) or 'none'})"
        for node in gap_nodes
    )

    # Build prompt safely: format header (no LLM data), then concatenate gap_summary
    # to avoid str.format() interpreting { } in concept names
    header = GAP_ENRICHMENT_PROMPT_HEADER.format(
        target_level=state.get("target_level", "mid"),
    )
    prompt = header + gap_summary + GAP_ENRICHMENT_PROMPT_FOOTER

    result = await ainvoke_structured(
        GapEnrichmentOutput,
        prompt,
        agent_name="gap_enricher.enrich",
    )

    # Merge LLM recommendations into enriched items
    rec_map = {r.concept: r.recommendation for r in result.recommendations}
    for item in enriched_items:
        item.recommendation = rec_map.get(
            item.skill_id,
            f"Focus on improving your understanding of {item.skill_name}.",
        )

    # Sort by priority (critical first), then gap size
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    enriched_items.sort(key=lambda x: (priority_order[x.priority], -x.gap))

    return {
        "enriched_gap_analysis": EnrichedGapAnalysis(
            overall_readiness=overall_readiness,
            summary=result.summary,
            gaps=enriched_items,
        )
    }
