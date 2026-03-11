from __future__ import annotations

from app.graph.state import AssessmentState, KnowledgeGraph, KnowledgeNode, bloom_index


def update_knowledge_graph(state: AssessmentState) -> dict:
    """Update the knowledge graph based on the latest evaluation result.

    Pure Python — no LLM call. Uses weighted averaging for confidence.
    """
    evaluation = state["latest_evaluation"]
    question = state["question_history"][-1]
    kg = state["knowledge_graph"]

    # Deep copy to avoid mutating state in place
    nodes = [n.model_copy(deep=True) for n in kg.nodes]
    edges = list(kg.edges)
    new_kg = KnowledgeGraph(nodes=nodes, edges=edges)

    existing = new_kg.get_node(question.topic)

    if existing:
        # Weighted merge: 70% old, 30% new
        new_confidence = 0.7 * existing.confidence + 0.3 * evaluation.confidence
        new_bloom = (
            evaluation.bloom_level
            if bloom_index(evaluation.bloom_level) > bloom_index(existing.bloom_level)
            else existing.bloom_level
        )
        updated = KnowledgeNode(
            concept=existing.concept,
            confidence=new_confidence,
            bloom_level=new_bloom,
            prerequisites=existing.prerequisites,
            evidence=existing.evidence + evaluation.evidence,
        )
        new_kg.upsert_node(updated)
    else:
        new_node = KnowledgeNode(
            concept=question.topic,
            confidence=evaluation.confidence,
            bloom_level=evaluation.bloom_level,
            prerequisites=_get_prerequisites_from_target(state, question.topic),
            evidence=evaluation.evidence,
        )
        new_kg.upsert_node(new_node)
        # Add prerequisite edges
        for prereq in new_node.prerequisites:
            if (prereq, question.topic) not in new_kg.edges:
                new_kg.edges.append((prereq, question.topic))

    # Track topic evaluation
    topics_evaluated = list(state.get("topics_evaluated", []))
    if question.topic not in topics_evaluated:
        topics_evaluated.append(question.topic)

    return {
        "knowledge_graph": new_kg,
        "topics_evaluated": topics_evaluated,
    }


def _get_prerequisites_from_target(state: AssessmentState, concept: str) -> list[str]:
    """Look up prerequisites from the target knowledge graph."""
    target = state.get("target_graph")
    if not target:
        return []
    target_node = target.get_node(concept)
    return target_node.prerequisites if target_node else []
