from __future__ import annotations

import uuid

from app.agents.schemas import QuestionOutput
from app.graph.state import AssessmentState, BloomLevel, Question
from app.prompts.question_gen import QUESTION_GEN_PROMPT
from app.services.ai import ainvoke_structured


async def generate_question(state: AssessmentState) -> dict:
    """Generate the next assessment question based on current state."""
    topic = state["current_topic"]
    bloom_level = state["current_bloom_level"]
    calibrated_level = state.get("calibrated_level", "mid")
    questions_on_topic = state.get("questions_on_current_topic", 0)

    # Collect previously used question types for this topic
    used_types = [q.question_type for q in state.get("question_history", []) if q.topic == topic]

    # Format previous questions for context
    prev_questions = (
        "\n".join(f"- [{q.topic}] {q.text}" for q in state.get("question_history", [])[-5:])
        or "None yet."
    )

    # bloom_level may be a string after checkpoint deserialization
    bloom_str = bloom_level.value if isinstance(bloom_level, BloomLevel) else str(bloom_level)

    prompt = QUESTION_GEN_PROMPT.format(
        topic=topic,
        bloom_level=bloom_str,
        calibrated_level=calibrated_level,
        questions_on_topic=questions_on_topic,
        used_types=", ".join(used_types) if used_types else "none",
        previous_questions=prev_questions,
    )

    result = await ainvoke_structured(
        QuestionOutput,
        prompt,
        agent_name="question_generator.generate",
    )

    question = Question(
        id=str(uuid.uuid4()),
        topic=result.topic or topic,
        bloom_level=BloomLevel(result.bloom_level or bloom_str),
        text=result.text,
        question_type=result.question_type or "conceptual",
    )

    question_history = list(state.get("question_history", []))
    question_history.append(question)

    return {
        "question_history": question_history,
        "pending_question": question,
        "questions_on_current_topic": questions_on_topic + 1,
    }
