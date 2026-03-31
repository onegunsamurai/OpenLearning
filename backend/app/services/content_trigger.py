from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI

from app.db import get_session_factory
from app.knowledge_base.loader import map_skills_to_domain
from app.repositories import session_repo

logger = logging.getLogger("openlearning.content")

_background_tasks: set[asyncio.Task] = set()


def trigger_content_pipeline(session_id: str, app: FastAPI) -> None:
    """Fire-and-forget background task to generate learning content for a completed assessment."""
    task = asyncio.create_task(_run_content_pipeline(session_id, app))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _run_content_pipeline(session_id: str, app: FastAPI) -> None:
    """Run the content generation pipeline for a given session."""
    try:
        # Determine domain from session's skill_ids
        domain = "backend_engineering"
        factory = get_session_factory()
        async with factory() as db:
            session_row = await session_repo.get_session(db, session_id)
            if session_row and session_row.skill_ids:
                domain = map_skills_to_domain(session_row.skill_ids)

        content_graph = app.state.content_graph
        config = {"configurable": {"thread_id": f"content-{session_id}"}}
        initial_state = {"session_id": session_id, "domain": domain}
        await content_graph.ainvoke(initial_state, config)
        logger.info("Content pipeline completed for session %s", session_id)
    except Exception:
        logger.exception("Content pipeline failed for session %s", session_id)
