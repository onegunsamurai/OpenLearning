from __future__ import annotations

from app.graph.state import AssessmentState
from app.models.knowledge import KnowledgeGraph, KnowledgeNode

# Discount applied when inferring confidence from assessed prerequisites.
# E.g. if a prerequisite was assessed at 0.82, the dependent concept gets 0.82 * 0.5 = 0.41.
PREREQ_DISCOUNT = 0.5


def get_effective_confidence(
    concept: str,
    current_kg: KnowledgeGraph,
    target_kg: KnowledgeGraph,
) -> float:
    """Return assessed confidence, or infer from prerequisites if un-assessed.

    For concepts not directly assessed, computes the discounted average of
    assessed prerequisite confidences. Returns 0.0 if no prerequisites were
    assessed or the concept has no prerequisites.
    """
    node = current_kg.get_node(concept)
    if node:
        return node.confidence

    target_node = target_kg.get_node(concept)
    if not target_node or not target_node.prerequisites:
        return 0.0

    prereq_confs: list[float] = []
    for prereq in target_node.prerequisites:
        prereq_node = current_kg.get_node(prereq)
        if prereq_node:
            prereq_confs.append(prereq_node.confidence)

    if not prereq_confs:
        return 0.0

    return (sum(prereq_confs) / len(prereq_confs)) * PREREQ_DISCOUNT


def analyze_gaps(state: AssessmentState) -> dict:
    """Diff current knowledge graph vs target graph.

    Pure Python — no LLM call. Finds concepts where
    current_confidence < target_confidence.
    Un-assessed concepts infer confidence from assessed prerequisites.
    Results are topologically sorted by prerequisites.
    """
    current_kg = state["knowledge_graph"]
    target_kg = state["target_graph"]

    gap_nodes: list[KnowledgeNode] = []

    for target_node in target_kg.nodes:
        current_confidence = get_effective_confidence(target_node.concept, current_kg, target_kg)
        current_node = current_kg.get_node(target_node.concept)

        # Gap exists if current is below target
        if current_confidence < target_node.confidence:
            gap_nodes.append(
                KnowledgeNode(
                    concept=target_node.concept,
                    confidence=current_confidence,
                    bloom_level=target_node.bloom_level,
                    prerequisites=target_node.prerequisites,
                    evidence=current_node.evidence if current_node else [],
                )
            )

    # Topological sort by prerequisites
    sorted_gaps = _topological_sort(gap_nodes)

    return {
        "gap_nodes": sorted_gaps,
        "assessment_complete": True,
    }


def _topological_sort(nodes: list[KnowledgeNode]) -> list[KnowledgeNode]:
    """Sort gap nodes so prerequisites come first."""
    concept_set = {n.concept for n in nodes}
    node_map = {n.concept: n for n in nodes}

    visited: set[str] = set()
    result: list[KnowledgeNode] = []

    def visit(concept: str) -> None:
        if concept in visited or concept not in concept_set:
            return
        visited.add(concept)
        node = node_map[concept]
        for prereq in node.prerequisites:
            if prereq in concept_set:
                visit(prereq)
        result.append(node)

    for node in nodes:
        visit(node.concept)

    return result
