from __future__ import annotations

from app.agents.schemas import PlanOutput
from app.graph.state import (
    AssessmentState,
    LearningPhase,
    LearningPlan,
    Resource,
)
from app.prompts.plan_generator import PLAN_GEN_PROMPT
from app.services.ai import ainvoke_structured


async def generate_plan(state: AssessmentState) -> dict:
    """Generate a learning plan from gap nodes."""
    gap_nodes = state["gap_nodes"]

    if not gap_nodes:
        return {
            "learning_plan": LearningPlan(
                phases=[],
                total_hours=0,
                summary="No significant gaps identified. Great job!",
            )
        }

    gap_summary = "\n".join(
        f"- {node.concept} (current confidence: {node.confidence:.1f}, "
        f"target bloom: {node.bloom_level.value}, "
        f"prerequisites: {', '.join(node.prerequisites) or 'none'})"
        for node in gap_nodes
    )

    prompt = PLAN_GEN_PROMPT.format(
        calibrated_level=state.get("calibrated_level", "unknown"),
        target_level=state.get("target_level", "mid"),
        gap_summary=gap_summary,
    )

    result = await ainvoke_structured(
        PlanOutput,
        prompt,
        agent_name="plan_generator.generate",
    )

    phases = []
    for p in result.phases:
        resources = [Resource(type=r.type, title=r.title, url=r.url) for r in p.resources]
        phases.append(
            LearningPhase(
                phase_number=p.phase_number,
                title=p.title,
                concepts=p.concepts,
                rationale=p.rationale,
                resources=resources,
                estimated_hours=p.estimated_hours,
            )
        )

    plan = LearningPlan(
        phases=phases,
        total_hours=result.total_hours,
        summary=result.summary,
    )

    return {"learning_plan": plan}
