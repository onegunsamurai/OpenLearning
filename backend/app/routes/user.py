from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import AssessmentResult, AssessmentSession, MaterialResult, get_db
from app.deps import AuthUser, get_current_user
from app.knowledge_base.loader import load_knowledge_base
from app.models.base import CamelModel

logger = logging.getLogger("openlearning.user")

router = APIRouter()


def _resolve_role_name(role_id: str | None) -> str | None:
    """Look up the display name for a role_id from the knowledge base."""
    if not role_id:
        return None
    try:
        kb = load_knowledge_base(role_id)
        return kb.display_name
    except Exception:
        return None


class UserAssessmentSummary(CamelModel):
    session_id: str
    status: str
    skill_ids: list[str]
    target_level: str
    role_id: str | None = None
    role_name: str | None = None
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
                role_id=session.role_id,
                role_name=_resolve_role_name(session.role_id),
                created_at=session.created_at,
                completed_at=completed_at,
                overall_readiness=overall_readiness,
                skill_count=len(session.skill_ids),
            )
        )

    return summaries


@router.delete("/assessments/{session_id}", status_code=204)
async def delete_user_assessment(
    session_id: str,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an assessment session owned by the current user."""
    session_row = await db.get(AssessmentSession, session_id)
    if not session_row:
        raise HTTPException(status_code=404, detail="Session not found")
    if session_row.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="Not your session")

    # Delete associated rows first (FK constraints)
    await db.execute(delete(MaterialResult).where(MaterialResult.session_id == session_id))
    await db.execute(delete(AssessmentResult).where(AssessmentResult.session_id == session_id))
    await db.delete(session_row)
    await db.commit()
