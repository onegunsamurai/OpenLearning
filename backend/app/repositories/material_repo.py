from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import MaterialResult


async def get_materials_by_session(
    db: AsyncSession,
    session_id: str,
) -> list[MaterialResult]:
    """Fetch all materials for a session."""
    result = await db.execute(select(MaterialResult).where(MaterialResult.session_id == session_id))
    return list(result.scalars().all())
