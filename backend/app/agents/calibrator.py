from __future__ import annotations

import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import (
    AssessmentState,
    BloomLevel,
    KnowledgeGraph,
    KnowledgeNode,
    Question,
)
from app.prompts.calibration import CALIBRATION_EVAL_PROMPT, CALIBRATION_QUESTION_PROMPT
from app.services.ai import get_chat_model, parse_json_response

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]


async def generate_calibration_question(state: AssessmentState, difficulty: str) -> Question:
    """Generate a single calibration question at the given difficulty."""
    domain = state["skill_domain"]
    prompt = CALIBRATION_QUESTION_PROMPT.format(domain=domain, difficulty=difficulty)

    model = get_chat_model()
    result = await model.ainvoke(
        [
            SystemMessage(
                content="You are a technical question generator. Respond only with JSON."
            ),
            HumanMessage(content=prompt),
        ]
    )

    text = result.content
    if not isinstance(text, str):
        raise ValueError("Unexpected response from calibration question generator")

    parsed = parse_json_response(text)

    return Question(
        id=str(uuid.uuid4()),
        topic=parsed.get("topic", "general"),
        bloom_level=BloomLevel.understand,
        text=parsed["text"],
        question_type=parsed.get("question_type", "conceptual"),
    )


async def evaluate_calibration(state: AssessmentState) -> dict:
    """Evaluate all 3 calibration Q&A pairs to determine starting level."""
    questions = state["calibration_questions"]
    responses = state["calibration_responses"]

    qa_pairs = ""
    for i, (q, r) in enumerate(zip(questions, responses, strict=False)):
        difficulty = DIFFICULTY_LEVELS[i] if i < len(DIFFICULTY_LEVELS) else "medium"
        qa_pairs += f"\n[{difficulty.upper()}] Q: {q.text}\nA: {r.text}\n"

    prompt = CALIBRATION_EVAL_PROMPT.format(qa_pairs=qa_pairs)

    model = get_chat_model()
    result = await model.ainvoke(
        [
            SystemMessage(content="You are an expert technical evaluator. Respond only with JSON."),
            HumanMessage(content=prompt),
        ]
    )

    text = result.content
    if not isinstance(text, str):
        raise ValueError("Unexpected response from calibration evaluator")

    parsed = parse_json_response(text)

    # Build initial knowledge graph from calibration
    nodes: list[KnowledgeNode] = []
    for concept_data in parsed.get("initial_concepts", []):
        nodes.append(
            KnowledgeNode(
                concept=concept_data["concept"],
                confidence=float(concept_data["confidence"]),
                bloom_level=BloomLevel(concept_data["bloom_level"]),
                prerequisites=[],
                evidence=["calibration"],
            )
        )

    calibrated_level = parsed.get("calibrated_level", "mid")
    first_topic = parsed.get("first_topic", "")

    # Determine starting bloom level based on calibrated level
    bloom_map = {
        "junior": BloomLevel.understand,
        "mid": BloomLevel.apply,
        "senior": BloomLevel.analyze,
        "staff": BloomLevel.evaluate,
    }

    return {
        "calibrated_level": calibrated_level,
        "knowledge_graph": KnowledgeGraph(nodes=nodes, edges=[]),
        "current_topic": first_topic,
        "current_bloom_level": bloom_map.get(calibrated_level, BloomLevel.apply),
    }
