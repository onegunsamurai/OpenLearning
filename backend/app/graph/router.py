from __future__ import annotations

from app.graph.state import (
    AssessmentState,
    BloomLevel,
    TopicStatus,
    bloom_index,
)

# Thresholds
MAX_TOPICS = 10
HIGH_CONFIDENCE = 0.7
MIN_EVIDENCE_FOR_CONFIDENCE = 2


def _get_max_questions_per_topic(state: AssessmentState) -> int:
    return state.get("max_questions_per_topic", 4)


def _get_max_total_questions(state: AssessmentState) -> int:
    agenda = state.get("topic_agenda", [])
    per_topic = _get_max_questions_per_topic(state)
    return min(len(agenda), MAX_TOPICS) * per_topic


def _count_assessed_topics(state: AssessmentState) -> int:
    agenda = state.get("topic_agenda", [])
    return sum(1 for item in agenda if item.status == TopicStatus.assessed)


def decide_branch(state: AssessmentState) -> str:
    """Deterministic routing after knowledge graph update.

    Returns one of:
        "conclude" — enough topics assessed or question budget exhausted
        "deeper"  — high confidence, push to higher Bloom level
        "probe"   — correct but insufficient evidence
        "pivot"   — topic confidence established or too many questions, move on
    """
    question_history = state.get("question_history", [])
    evaluation = state.get("latest_evaluation")
    current_topic = state.get("current_topic", "")
    current_bloom = state.get("current_bloom_level", BloomLevel.understand)
    questions_on_topic = state.get("questions_on_current_topic", 0)
    knowledge_graph = state.get("knowledge_graph")
    max_per_topic = _get_max_questions_per_topic(state)
    max_total = _get_max_total_questions(state)

    # 1. Conclude: enough topics assessed, budget exhausted, or no remaining topics
    assessed_count = _count_assessed_topics(state)
    agenda = state.get("topic_agenda", [])
    has_remaining = any(item.status in (TopicStatus.pending, TopicStatus.active) for item in agenda)
    if assessed_count >= MAX_TOPICS or len(question_history) >= max_total:
        return "conclude"
    if agenda and not has_remaining:
        return "conclude"

    if not evaluation:
        return "pivot"

    confidence = evaluation.confidence
    evidence_count = len(evaluation.evidence)

    # Get current node confidence from KG
    node_confidence = 0.0
    if knowledge_graph:
        node = knowledge_graph.get_node(current_topic)
        if node:
            node_confidence = node.confidence

    # 2. Deeper: high confidence + room to go up in Bloom
    if (
        confidence > HIGH_CONFIDENCE
        and bloom_index(current_bloom) < bloom_index(BloomLevel.create)
        and questions_on_topic < max_per_topic
    ):
        return "deeper"

    # 3. Probe: answer was okay but low evidence — need more data
    if (
        confidence > 0.4
        and evidence_count < MIN_EVIDENCE_FOR_CONFIDENCE
        and questions_on_topic < max_per_topic
    ):
        return "probe"

    # 4. Pivot: confidence is established (high or low) or too many questions on topic
    if node_confidence > HIGH_CONFIDENCE or questions_on_topic >= max_per_topic:
        return "pivot"

    # Default: if low confidence, pivot to expose more gaps
    if confidence <= 0.4:
        return "pivot"

    # Otherwise keep probing
    return "probe"


def get_next_topic(state: AssessmentState) -> dict:
    """Select the next topic from the agenda, updating status accordingly."""
    agenda = [item.model_copy(deep=True) for item in state.get("topic_agenda", [])]

    # Mark current topic as assessed if it was active
    current_topic = state.get("current_topic", "")
    knowledge_graph = state.get("knowledge_graph")
    for item in agenda:
        if item.concept == current_topic and item.status == TopicStatus.active:
            item.status = TopicStatus.assessed
            if knowledge_graph:
                node = knowledge_graph.get_node(current_topic)
                if node:
                    item.confidence = node.confidence

    # Find first pending topic
    next_topic = ""
    for item in agenda:
        if item.status == TopicStatus.pending:
            item.status = TopicStatus.active
            next_topic = item.concept
            break

    if not next_topic:
        # All topics covered — shouldn't normally reach here
        # Return empty to trigger conclude on next cycle
        return {
            "topic_agenda": agenda,
            "current_topic": "",
            "questions_on_current_topic": 0,
        }

    # Determine starting bloom level based on calibrated level
    calibrated_level = state.get("calibrated_level", "mid")
    bloom_map = {
        "junior": BloomLevel.understand,
        "mid": BloomLevel.apply,
        "senior": BloomLevel.analyze,
        "staff": BloomLevel.evaluate,
    }

    return {
        "topic_agenda": agenda,
        "current_topic": next_topic,
        "current_bloom_level": bloom_map.get(calibrated_level, BloomLevel.apply),
        "questions_on_current_topic": 0,
    }


def get_deeper_bloom(state: AssessmentState) -> dict:
    """Advance to the next Bloom level for the current topic."""
    current_bloom = state.get("current_bloom_level", BloomLevel.understand)
    idx = bloom_index(current_bloom)
    from app.graph.state import BLOOM_ORDER

    next_bloom = BLOOM_ORDER[min(idx + 1, len(BLOOM_ORDER) - 1)]

    return {
        "current_bloom_level": next_bloom,
    }
