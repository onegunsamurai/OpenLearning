from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from app.db import AssessmentSession, _get_session_factory

logger = logging.getLogger("openlearning.session_cleanup")


async def cleanup_stale_sessions(
    interval_seconds: int = 300,
    timeout_minutes: int = 30,
) -> None:
    """Background task that periodically marks stale active sessions as timed_out.

    Runs every ``interval_seconds`` (default 5 min). Any session with status='active'
    and ``updated_at`` older than ``timeout_minutes`` is set to 'timed_out'.
    """
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            cutoff = datetime.now(UTC) - timedelta(minutes=timeout_minutes)
            factory = _get_session_factory()
            async with factory() as session:
                result = await session.execute(
                    update(AssessmentSession)
                    .where(
                        AssessmentSession.status == "active",
                        AssessmentSession.updated_at < cutoff,
                    )
                    .values(status="timed_out")
                )
                await session.commit()
                if result.rowcount:
                    logger.info(
                        "Marked stale sessions as timed_out",
                        extra={"count": result.rowcount},
                    )
        except Exception:
            logger.exception("Error during session cleanup")
