from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AssessmentResult


async def get_result_by_session(
    db: AsyncSession,
    session_id: str,
) -> AssessmentResult | None:
    """Fetch the assessment result for a session."""
    result = await db.execute(
        select(AssessmentResult).where(AssessmentResult.session_id == session_id)
    )
    return result.scalar_one_or_none()
