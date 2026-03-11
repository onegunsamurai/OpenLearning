from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph.state import (
    AssessmentState,
    LearningPhase,
    LearningPlan,
    Resource,
)
from app.services.ai import get_chat_model, parse_json_response

PLAN_GEN_PROMPT = """You are a learning engineer creating a personalized learning plan.

The candidate was assessed at level "{calibrated_level}" targeting "{target_level}" in backend engineering.

Knowledge gaps (sorted by prerequisite order):
{gap_summary}

Create a phased learning plan that:
1. Groups gaps into 3-5 phases, respecting prerequisite order
2. Each phase should build on the previous
3. Include specific resources (real documentation, courses, books)
4. Estimate realistic hours per phase
5. Mix resource types: video, article, project, exercise

Respond with ONLY a JSON object:
{{
  "summary": "2-3 sentence plan overview",
  "total_hours": 40,
  "phases": [
    {{
      "phase_number": 1,
      "title": "Phase title",
      "concepts": ["concept1", "concept2"],
      "rationale": "Why these concepts are grouped and ordered this way",
      "resources": [
        {{"type": "article", "title": "Resource name", "url": "https://..."}},
        {{"type": "project", "title": "Hands-on exercise", "url": null}}
      ],
      "estimated_hours": 10
    }}
  ]
}}"""


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

    model = get_chat_model()
    result = await model.ainvoke(
        [
            SystemMessage(content="You are a learning engineer. Respond only with JSON."),
            HumanMessage(content=prompt),
        ]
    )

    text = result.content
    if not isinstance(text, str):
        raise ValueError("Unexpected response from plan generator")

    parsed = parse_json_response(text)

    phases = []
    for p in parsed.get("phases", []):
        resources = []
        for r in p.get("resources", []):
            resources.append(
                Resource(
                    type=r.get("type", "article"),
                    title=r.get("title", ""),
                    url=r.get("url"),
                )
            )
        phases.append(
            LearningPhase(
                phase_number=p["phase_number"],
                title=p["title"],
                concepts=p.get("concepts", []),
                rationale=p.get("rationale", ""),
                resources=resources,
                estimated_hours=float(p.get("estimated_hours", 0)),
            )
        )

    plan = LearningPlan(
        phases=phases,
        total_hours=float(parsed.get("total_hours", sum(p.estimated_hours for p in phases))),
        summary=parsed.get("summary", ""),
    )

    return {"learning_plan": plan}
