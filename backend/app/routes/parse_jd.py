from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage

from app.models.jd_parser import JDParseRequest, JDParseResponse
from app.prompts.jd_parser import JD_PARSER_SYSTEM_PROMPT
from app.services.ai import get_chat_model, parse_json_response

router = APIRouter()


@router.post("/parse-jd", response_model=JDParseResponse, response_model_by_alias=True)
async def parse_jd(request: JDParseRequest) -> JDParseResponse:
    if not request.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required")

    try:
        model = get_chat_model()
        response = await model.ainvoke(
            [
                SystemMessage(content=JD_PARSER_SYSTEM_PROMPT),
                HumanMessage(content=request.job_description),
            ]
        )

        text = response.content
        if not isinstance(text, str):
            raise ValueError("Unexpected response format")

        parsed = parse_json_response(text)

        if not isinstance(parsed.get("skills"), list) or not isinstance(parsed.get("summary"), str):
            raise ValueError("Invalid response format")

        return JDParseResponse(skills=parsed["skills"], summary=parsed["summary"])
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse job description: {e}") from e
