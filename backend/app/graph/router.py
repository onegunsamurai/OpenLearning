from __future__ import annotations

from app.graph.state import AssessmentState, BloomLevel, bloom_index

# Thresholds
MAX_TOPICS = 8
MAX_TOTAL_QUESTIONS = 25
HIGH_CONFIDENCE = 0.7
MAX_QUESTIONS_PER_TOPIC = 4
MIN_EVIDENCE_FOR_CONFIDENCE = 2


def decide_branch(state: AssessmentState) -> str:
    """Deterministic routing after knowledge graph update.

    Returns one of:
        "conclude" — enough topics evaluated or question budget exhausted
        "deeper"  — high confidence, push to higher Bloom level
        "probe"   — correct but insufficient evidence
        "pivot"   — topic confidence established or too many questions, move on
    """
    topics_evaluated = state.get("topics_evaluated", [])
    question_history = state.get("question_history", [])
    evaluation = state.get("latest_evaluation")
    current_topic = state.get("current_topic", "")
    current_bloom = state.get("current_bloom_level", BloomLevel.understand)
    questions_on_topic = state.get("questions_on_current_topic", 0)
    knowledge_graph = state.get("knowledge_graph")

    # 1. Conclude: enough coverage or budget exhausted
    if len(topics_evaluated) >= MAX_TOPICS or len(question_history) >= MAX_TOTAL_QUESTIONS:
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
        and questions_on_topic < MAX_QUESTIONS_PER_TOPIC
    ):
        return "deeper"

    # 3. Probe: answer was okay but low evidence — need more data
    if (
        confidence > 0.4
        and evidence_count < MIN_EVIDENCE_FOR_CONFIDENCE
        and questions_on_topic < MAX_QUESTIONS_PER_TOPIC
    ):
        return "probe"

    # 4. Pivot: confidence is established (high or low) or too many questions on topic
    if node_confidence > HIGH_CONFIDENCE or questions_on_topic >= MAX_QUESTIONS_PER_TOPIC:
        return "pivot"

    # Default: if low confidence, pivot to expose more gaps
    if confidence <= 0.4:
        return "pivot"

    # Otherwise keep probing
    return "probe"


def get_next_topic(state: AssessmentState) -> dict:
    """Select the next topic to assess, updating state accordingly."""
    from app.knowledge_base.loader import get_all_topics

    topics_evaluated = set(state.get("topics_evaluated", []))
    domain = state.get("skill_domain", "backend_engineering")
    target_level = state.get("target_level", "mid")

    all_topics = get_all_topics(domain, target_level)

    # Pick the first unevaluated topic
    next_topic = ""
    for topic in all_topics:
        if topic not in topics_evaluated:
            next_topic = topic
            break

    if not next_topic and all_topics:
        # All topics covered — shouldn't reach here, but fallback
        next_topic = all_topics[0]

    # Determine starting bloom level based on calibrated level
    calibrated_level = state.get("calibrated_level", "mid")
    bloom_map = {
        "junior": BloomLevel.understand,
        "mid": BloomLevel.apply,
        "senior": BloomLevel.analyze,
        "staff": BloomLevel.evaluate,
    }

    return {
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
