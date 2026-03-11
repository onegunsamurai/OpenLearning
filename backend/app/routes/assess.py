import asyncio

from fastapi import APIRouter
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from starlette.responses import StreamingResponse

from app.models.assessment import AssessRequest
from app.prompts.assessor import get_assessor_system_prompt
from app.services.ai import get_chat_model

router = APIRouter()


@router.post("/assess")
async def assess(request: AssessRequest) -> StreamingResponse:
    model = get_chat_model()

    langchain_messages: list[BaseMessage] = [
        SystemMessage(content=get_assessor_system_prompt(request.skill_names)),
    ]

    if not request.messages:
        langchain_messages.append(HumanMessage(content="Begin the assessment."))

    for msg in request.messages:
        if msg.role == "user":
            langchain_messages.append(HumanMessage(content=msg.content))
        else:
            langchain_messages.append(AIMessage(content=msg.content))

    async def event_stream():
        try:
            async for chunk in model.astream(langchain_messages):
                text = chunk.content if isinstance(chunk.content, str) else ""
                if text:
                    yield f"data: {text}\n\n"
            yield "data: [DONE]\n\n"
        except asyncio.CancelledError:
            return
        except Exception as e:
            yield f"data: [ERROR] {e}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
