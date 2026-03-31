"""Assessment route handlers — thin HTTP wrappers around the service layer."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import PlainTextResponse, StreamingResponse

from app.db import get_db
from app.deps import AuthUser, get_current_user, get_user_api_key
from app.models.assessment_api import (
    AssessmentReportResponse,
    AssessmentRespondRequest,
    AssessmentStartRequest,
    AssessmentStartResponse,
    KnowledgeGraphOut,
)
from app.services import assessment_service as service
from app.services.content_trigger import trigger_content_pipeline
from app.services.sse_adapter import SSEAdapter

router = APIRouter()


@router.post(
    "/assessment/start", response_model=AssessmentStartResponse, response_model_by_alias=True
)
async def assessment_start(
    request: AssessmentStartRequest,
    req: Request,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_user_api_key),
) -> AssessmentStartResponse:
    return await service.start_assessment(db, req.app.state.graph, user, request, api_key)


@router.post("/assessment/{session_id}/respond")
async def assessment_respond(
    session_id: str,
    request: AssessmentRespondRequest,
    req: Request,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_user_api_key),
) -> StreamingResponse:
    events = await service.respond_to_assessment(
        db, req.app.state.graph, session_id, user, request.response, api_key
    )
    return StreamingResponse(
        SSEAdapter().adapt(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get(
    "/assessment/{session_id}/graph", response_model=KnowledgeGraphOut, response_model_by_alias=True
)
async def assessment_graph(
    session_id: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> KnowledgeGraphOut:
    return await service.get_assessment_graph(db, req.app.state.graph, session_id, user)


@router.get(
    "/assessment/{session_id}/report",
    response_model=AssessmentReportResponse,
    response_model_by_alias=True,
)
async def assessment_report(
    session_id: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> AssessmentReportResponse:
    result = await service.get_assessment_report(db, req.app.state.graph, session_id, user)
    if result.first_completion:
        trigger_content_pipeline(session_id, req.app)
    return result.report


@router.get("/assessment/{session_id}/export")
async def assessment_export(
    session_id: str,
    req: Request,
    db: AsyncSession = Depends(get_db),
    user: AuthUser = Depends(get_current_user),
) -> PlainTextResponse:
    result = await service.export_assessment(db, req.app.state.graph, session_id, user)
    return PlainTextResponse(
        content=result.markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="assessment-{result.session_id[:8]}.md"',
        },
    )


@router.get(
    "/assessment/{session_id}/resume",
    response_model=AssessmentStartResponse,
    response_model_by_alias=True,
)
async def assessment_resume(
    session_id: str,
    req: Request,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(get_user_api_key),
) -> AssessmentStartResponse:
    """Resume an active assessment session by loading the pending interrupt."""
    return await service.resume_assessment(db, req.app.state.graph, session_id, user)
