from __future__ import annotations

import uuid

from app.agents.schemas import CalibrationEvalOutput, CalibrationQuestionOutput
from app.graph.state import (
    AssessmentState,
    BloomLevel,
    KnowledgeGraph,
    KnowledgeNode,
    Question,
)
from app.prompts.calibration import CALIBRATION_EVAL_PROMPT, CALIBRATION_QUESTION_PROMPT
from app.services.ai import ainvoke_structured

DIFFICULTY_LEVELS = ["easy", "medium", "hard"]


async def generate_calibration_question(state: AssessmentState, difficulty: str) -> Question:
    """Generate a single calibration question at the given difficulty."""
    domain = state["skill_domain"]
    prompt = CALIBRATION_QUESTION_PROMPT.format(domain=domain, difficulty=difficulty)

    result = await ainvoke_structured(
        CalibrationQuestionOutput,
        prompt,
        agent_name="calibrator.generate_question",
    )

    return Question(
        id=str(uuid.uuid4()),
        topic=result.topic,
        bloom_level=BloomLevel.understand,
        text=result.text,
        question_type=result.question_type,
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

    result = await ainvoke_structured(
        CalibrationEvalOutput,
        prompt,
        agent_name="calibrator.evaluate",
    )

    # Build initial knowledge graph from calibration
    nodes: list[KnowledgeNode] = []
    for concept_data in result.initial_concepts:
        nodes.append(
            KnowledgeNode(
                concept=concept_data.concept,
                confidence=float(concept_data.confidence),
                bloom_level=BloomLevel(concept_data.bloom_level),
                prerequisites=[],
                evidence=["calibration"],
            )
        )

    calibrated_level = result.calibrated_level

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
        "current_topic": result.first_topic,
        "current_bloom_level": bloom_map.get(calibrated_level, BloomLevel.apply),
    }
