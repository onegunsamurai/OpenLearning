from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db import AssessmentResult, AssessmentSession, MaterialResult


async def get_session(
    db: AsyncSession,
    session_id: str,
) -> AssessmentSession | None:
    """Fetch a session by primary key. Returns None if not found."""
    return await db.get(AssessmentSession, session_id)


async def get_session_with_ownership(
    db: AsyncSession,
    session_id: str,
    user_id: str,
) -> AssessmentSession:
    """Fetch session, raise 404 if missing, 403 if not owned by user_id."""
    session = await db.get(AssessmentSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your session")
    return session


async def list_user_sessions(
    db: AsyncSession,
    user_id: str,
) -> list[AssessmentSession]:
    """List all sessions for a user, ordered by creation date desc, with results eagerly loaded."""
    query = (
        select(AssessmentSession)
        .options(joinedload(AssessmentSession.result))
        .where(AssessmentSession.user_id == user_id)
        .order_by(AssessmentSession.created_at.desc())
    )
    rows = await db.execute(query)
    return list(rows.unique().scalars().all())


async def delete_session_cascade(
    db: AsyncSession,
    session: AssessmentSession,
) -> None:
    """Delete a session and its associated results/materials. Caller must commit."""
    session_id = session.session_id
    await db.execute(delete(MaterialResult).where(MaterialResult.session_id == session_id))
    await db.execute(delete(AssessmentResult).where(AssessmentResult.session_id == session_id))
    await db.delete(session)


async def timeout_stale_sessions(
    db: AsyncSession,
    cutoff: datetime,
) -> int:
    """Mark active sessions older than cutoff as timed_out. Caller must commit."""
    result = await db.execute(
        update(AssessmentSession)
        .where(
            AssessmentSession.status == "active",
            AssessmentSession.updated_at < cutoff,
        )
        .values(status="timed_out")
    )
    return result.rowcount
