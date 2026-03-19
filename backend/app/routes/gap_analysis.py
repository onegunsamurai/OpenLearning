import json

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage

from app.deps import AuthUser, get_current_user
from app.models.gap_analysis import GapAnalysis, GapAnalysisRequest
from app.prompts.gap_analyzer import GAP_ANALYZER_SYSTEM_PROMPT
from app.services.ai import get_chat_model, parse_json_response

router = APIRouter()


@router.post("/gap-analysis", response_model=GapAnalysis, response_model_by_alias=True)
async def gap_analysis(
    request: GapAnalysisRequest,
    user: AuthUser = Depends(get_current_user),
) -> GapAnalysis:
    if not request.proficiency_scores:
        raise HTTPException(status_code=400, detail="Proficiency scores are required")

    try:
        scores_json = json.dumps(
            [s.model_dump(by_alias=True) for s in request.proficiency_scores],
            indent=2,
        )
        prompt = (
            f"Here are the proficiency scores from a skill assessment:\n\n"
            f"{scores_json}\n\n"
            f"Generate a comprehensive gap analysis."
        )

        model = get_chat_model()
        response = await model.ainvoke(
            [
                SystemMessage(content=GAP_ANALYZER_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )

        text = response.content
        if not isinstance(text, str):
            raise ValueError("Unexpected response format")

        parsed = parse_json_response(text)

        if not isinstance(parsed.get("overallReadiness"), int | float) or not isinstance(
            parsed.get("gaps"), list
        ):
            raise ValueError("Invalid response format")

        return GapAnalysis(**parsed)
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate gap analysis: {e}") from e
