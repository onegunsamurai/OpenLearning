from __future__ import annotations

from app.agents.schemas import EvaluationOutput
from app.graph.state import AssessmentState, BloomLevel, EvaluationResult
from app.knowledge_base.loader import load_knowledge_base
from app.prompts.evaluator import EVALUATOR_PROMPT
from app.services.ai import ainvoke_structured


async def evaluate_response(state: AssessmentState) -> dict:
    """Evaluate the candidate's latest response against the question asked."""
    question = state["question_history"][-1]
    response = state["response_history"][-1]

    bloom = question.bloom_level
    bloom_str = bloom.value if isinstance(bloom, BloomLevel) else str(bloom)

    skill_domain = state.get("skill_domain", "backend_engineering")
    domain_display = load_knowledge_base(skill_domain).display_name

    prompt = EVALUATOR_PROMPT.format(
        domain=domain_display,
        topic=question.topic,
        bloom_level=bloom_str,
        question_text=question.text,
        response_text=response.text,
    )

    result = await ainvoke_structured(
        EvaluationOutput,
        prompt,
        agent_name="response_evaluator.evaluate",
    )

    evaluation = EvaluationResult(
        question_id=question.id,
        confidence=max(0.0, min(1.0, result.confidence)),
        bloom_level=BloomLevel(result.bloom_level),
        evidence=result.evidence,
    )

    return {"latest_evaluation": evaluation}
