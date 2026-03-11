from __future__ import annotations

import uuid

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import AssessmentState, BloomLevel, Question
from app.prompts.question_gen import QUESTION_GEN_PROMPT
from app.services.ai import get_chat_model, parse_json_response


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

    prompt = QUESTION_GEN_PROMPT.format(
        topic=topic,
        bloom_level=bloom_level.value,
        calibrated_level=calibrated_level,
        questions_on_topic=questions_on_topic,
        used_types=", ".join(used_types) if used_types else "none",
        previous_questions=prev_questions,
    )

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
        raise ValueError("Unexpected response format from question generator")

    parsed = parse_json_response(text)

    question = Question(
        id=str(uuid.uuid4()),
        topic=parsed.get("topic", topic),
        bloom_level=BloomLevel(parsed.get("bloom_level", bloom_level.value)),
        text=parsed["text"],
        question_type=parsed.get("question_type", "conceptual"),
    )

    question_history = list(state.get("question_history", []))
    question_history.append(question)

    return {
        "question_history": question_history,
        "pending_question": question,
        "questions_on_current_topic": questions_on_topic + 1,
    }
