from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from app.db import get_session_factory
from app.repositories import session_repo

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
            factory = get_session_factory()
            async with factory() as db:
                count = await session_repo.timeout_stale_sessions(db, cutoff)
                await db.commit()
                if count:
                    logger.info(
                        "Marked stale sessions as timed_out",
                        extra={"count": count},
                    )
        except Exception:
            logger.exception("Error during session cleanup")
