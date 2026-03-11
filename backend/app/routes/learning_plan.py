import json

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.learning_plan import LearningPlan, LearningPlanRequest
from app.prompts.plan_generator import PLAN_GENERATOR_SYSTEM_PROMPT
from app.services.ai import get_chat_model, parse_json_response

router = APIRouter()


@router.post("/learning-plan", response_model=LearningPlan, response_model_by_alias=True)
async def learning_plan(request: LearningPlanRequest) -> LearningPlan:
    if not request.gap_analysis or not request.gap_analysis.gaps:
        raise HTTPException(status_code=400, detail="Gap analysis data is required")

    try:
        gap_json = json.dumps(
            request.gap_analysis.model_dump(by_alias=True),
            indent=2,
        )
        prompt = (
            f"Here is the gap analysis:\n\n"
            f"{gap_json}\n\n"
            f"Generate a personalized learning plan addressing these gaps."
        )

        model = get_chat_model()
        response = await model.ainvoke(
            [
                SystemMessage(content=PLAN_GENERATOR_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )

        text = response.content
        if not isinstance(text, str):
            raise ValueError("Unexpected response format")

        parsed = parse_json_response(text)

        if not isinstance(parsed.get("phases"), list) or not isinstance(parsed.get("title"), str):
            raise ValueError("Invalid response format")

        return LearningPlan(**parsed)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate learning plan: {e}") from e
