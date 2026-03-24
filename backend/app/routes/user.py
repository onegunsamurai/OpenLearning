from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import AssessmentSession, get_db
from app.deps import AuthUser, get_current_user
from app.models.base import CamelModel

router = APIRouter()


class UserAssessmentSummary(CamelModel):
    session_id: str
    status: str
    skill_ids: list[str]
    target_level: str
    created_at: datetime
    completed_at: datetime | None = None
    overall_readiness: int | None = None
    skill_count: int


@router.get(
    "/assessments",
    response_model=list[UserAssessmentSummary],
    response_model_by_alias=True,
)
async def list_user_assessments(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserAssessmentSummary]:
    """List all assessment sessions for the current user."""
    query = (
        select(AssessmentSession)
        .options(joinedload(AssessmentSession.result))
        .where(AssessmentSession.user_id == user.user_id)
        .order_by(AssessmentSession.created_at.desc())
    )
    rows = await db.execute(query)
    sessions = rows.unique().scalars().all()

    summaries = []
    for session in sessions:
        overall_readiness = None
        completed_at = None

        if session.result:
            completed_at = session.result.completed_at
            enriched = session.result.enriched_gap_analysis
            if enriched and isinstance(enriched, dict):
                overall_readiness = enriched.get("overall_readiness")

        summaries.append(
            UserAssessmentSummary(
                session_id=session.session_id,
                status=session.status,
                skill_ids=session.skill_ids,
                target_level=session.target_level,
                created_at=session.created_at,
                completed_at=completed_at,
                overall_readiness=overall_readiness,
                skill_count=len(session.skill_ids),
            )
        )

    return summaries
