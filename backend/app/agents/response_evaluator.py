from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import AssessmentState, BloomLevel, EvaluationResult
from app.prompts.evaluator import EVALUATOR_PROMPT
from app.services.ai import get_chat_model, parse_json_response


async def evaluate_response(state: AssessmentState) -> dict:
    """Evaluate the candidate's latest response against the question asked."""
    question = state["question_history"][-1]
    response = state["response_history"][-1]

    prompt = EVALUATOR_PROMPT.format(
        topic=question.topic,
        bloom_level=question.bloom_level.value,
        question_text=question.text,
        response_text=response.text,
    )

    model = get_chat_model()
    result = await model.ainvoke(
        [
            SystemMessage(
                content="You are a technical assessment evaluator. Respond only with JSON."
            ),
            HumanMessage(content=prompt),
        ]
    )

    text = result.content
    if not isinstance(text, str):
        raise ValueError("Unexpected response format from evaluator")

    parsed = parse_json_response(text)

    evaluation = EvaluationResult(
        question_id=question.id,
        confidence=max(0.0, min(1.0, float(parsed["confidence"]))),
        bloom_level=BloomLevel(parsed["bloom_level"]),
        evidence=parsed.get("evidence", []),
    )

    return {"latest_evaluation": evaluation}
