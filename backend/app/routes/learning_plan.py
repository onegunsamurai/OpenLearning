from __future__ import annotations

import json
import logging

from anthropic import APIError
from fastapi import APIRouter, Depends, HTTPException

from app.agents.schemas import LearningPlanOutput
from app.deps import AuthUser, get_current_user, get_user_api_key
from app.models.learning_plan import LearningPlan, LearningPlanRequest
from app.prompts.plan_generator import PLAN_GENERATOR_SYSTEM_PROMPT
from app.services.ai import ainvoke_structured, api_key_scope

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
            f"{PLAN_GENERATOR_SYSTEM_PROMPT}\n\n"
            f"Here is the gap analysis:\n\n"
            f"{gap_json}\n\n"
            f"Generate a personalized learning plan addressing these gaps."
        )

        with api_key_scope(api_key):
            result = await ainvoke_structured(
                LearningPlanOutput, prompt, agent_name="learning_plan"
            )

        return LearningPlan.model_validate(result.model_dump())
    except (HTTPException, APIError):
        raise
    except Exception as e:
        logger.exception("Learning plan generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate learning plan") from e
