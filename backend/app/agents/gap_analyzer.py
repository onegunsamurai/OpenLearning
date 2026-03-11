from __future__ import annotations

from app.graph.state import AssessmentState, KnowledgeNode


def analyze_gaps(state: AssessmentState) -> dict:
    """Diff current knowledge graph vs target graph.

    Pure Python — no LLM call. Finds concepts where
    current_confidence < target_confidence - 0.2 (tolerance).
    Results are topologically sorted by prerequisites.
    """
    current_kg = state["knowledge_graph"]
    target_kg = state["target_graph"]

    gap_nodes: list[KnowledgeNode] = []

    for target_node in target_kg.nodes:
        current_node = current_kg.get_node(target_node.concept)
        current_confidence = current_node.confidence if current_node else 0.0

        # Gap exists if current is more than 0.2 below target
        if current_confidence < target_node.confidence - 0.2:
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
