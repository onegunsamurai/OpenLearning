from __future__ import annotations

from app.agents.gap_analyzer import PREREQ_DISCOUNT
from app.graph.state import AssessmentState
from app.models.assessment_pipeline import AgendaItem, TopicStatus
from app.models.bloom import BloomLevel, bloom_index
from app.models.knowledge import KnowledgeGraph, KnowledgeNode


def update_knowledge_graph(state: AssessmentState) -> dict:
    """Update the knowledge graph based on the latest evaluation result.

    Pure Python — no LLM call. Uses weighted averaging for confidence.
    After updating the assessed topic, propagates discounted confidence
    to its prerequisites and updates agenda status accordingly.
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

    # Propagate confidence to prerequisites
    assessed_node = new_kg.get_node(question.topic)
    agenda = _propagate_prereq_confidence(state, new_kg, assessed_node)

    result: dict = {
        "knowledge_graph": new_kg,
        "topics_evaluated": topics_evaluated,
    }
    if agenda is not None:
        result["topic_agenda"] = agenda

    return result


def _propagate_prereq_confidence(
    state: AssessmentState,
    kg: KnowledgeGraph,
    assessed_node: KnowledgeNode | None,
) -> list[AgendaItem] | None:
    """Propagate discounted confidence from an assessed topic to its prerequisites.

    When a topic is assessed, this infers confidence for its prerequisite topics
    as (assessed_confidence * PREREQ_DISCOUNT), but only for prerequisites that
    do not yet exist as nodes in the knowledge graph. Existing prerequisite nodes
    are never modified by this function. Also updates agenda status for
    prerequisite items.
    """
    if not assessed_node or not assessed_node.prerequisites:
        return None

    agenda = state.get("topic_agenda", [])
    if not agenda:
        return None

    agenda = [item.model_copy(deep=True) for item in agenda]
    changed = False

    for prereq_name in assessed_node.prerequisites:
        inferred_conf = assessed_node.confidence * PREREQ_DISCOUNT
        existing_prereq = kg.get_node(prereq_name)

        if existing_prereq:
            # Never overwrite — assessed or previously inferred data takes precedence
            pass
        else:
            # Create a new node for the prerequisite with inferred confidence
            new_prereq = KnowledgeNode(
                concept=prereq_name,
                confidence=inferred_conf,
                bloom_level=BloomLevel.understand,
                prerequisites=_get_prerequisites_from_target(state, prereq_name),
                evidence=[f"Inferred from {assessed_node.concept}"],
            )
            kg.upsert_node(new_prereq)
            changed = True

        # Update agenda status for the prerequisite
        for item in agenda:
            if item.concept == prereq_name and item.status == TopicStatus.pending:
                item.status = TopicStatus.inferred
                item.confidence = max(item.confidence, inferred_conf)
                changed = True

    return agenda if changed else None


def _get_prerequisites_from_target(state: AssessmentState, concept: str) -> list[str]:
    """Look up prerequisites from the target knowledge graph."""
    target = state.get("target_graph")
    if not target:
        return []
    target_node = target.get_node(concept)
    return target_node.prerequisites if target_node else []
