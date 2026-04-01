from __future__ import annotations

import json
import logging

from anthropic import APIError
from fastapi import APIRouter, Depends, HTTPException

from app.agents.schemas import GapAnalysisOutput
from app.deps import AuthUser, get_current_user, get_user_api_key
from app.models.gap_analysis import GapAnalysis, GapAnalysisRequest
from app.prompts.gap_analyzer import GAP_ANALYZER_SYSTEM_PROMPT
from app.services.ai import ainvoke_structured, api_key_scope

logger = logging.getLogger("openlearning.gap_analysis")

router = APIRouter()


@router.post("/gap-analysis", response_model=GapAnalysis, response_model_by_alias=True)
async def gap_analysis(
    request: GapAnalysisRequest,
    user: AuthUser = Depends(get_current_user),
    api_key: str = Depends(get_user_api_key),
) -> GapAnalysis:
    if not request.proficiency_scores:
        raise HTTPException(status_code=400, detail="Proficiency scores are required")

    try:
        scores_json = json.dumps(
            [s.model_dump(by_alias=True) for s in request.proficiency_scores],
            indent=2,
        )
        prompt = (
            f"{GAP_ANALYZER_SYSTEM_PROMPT}\n\n"
            f"Here are the proficiency scores from a skill assessment:\n\n"
            f"{scores_json}\n\n"
            f"Generate a comprehensive gap analysis."
        )

        with api_key_scope(api_key):
            result = await ainvoke_structured(GapAnalysisOutput, prompt, agent_name="gap_analysis")

        return GapAnalysis.model_validate(result.model_dump())
    except (HTTPException, APIError):
        raise
    except Exception as e:
        logger.exception("Gap analysis generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate gap analysis") from e
