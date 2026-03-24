import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage

from app.deps import AuthUser, get_current_user, get_user_api_key
from app.models.learning_plan import LearningPlan, LearningPlanRequest
from app.prompts.plan_generator import PLAN_GENERATOR_SYSTEM_PROMPT
from app.services.ai import get_chat_model, parse_json_response

logger = logging.getLogger("openlearning.learning_plan")

router = APIRouter()


@router.post("/learning-plan", response_model=LearningPlan, response_model_by_alias=True)
async def learning_plan(
    request: LearningPlanRequest,
    user: AuthUser = Depends(get_current_user),
    api_key: str = Depends(get_user_api_key),
) -> LearningPlan:
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

        model = get_chat_model(api_key=api_key)
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
        logger.exception("Learning plan generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate learning plan") from e
