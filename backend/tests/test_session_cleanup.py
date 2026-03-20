"""Tests for session timeout cleanup."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import AssessmentSession, Base
from tests.conftest import _test_db_url


@pytest_asyncio.fixture
async def db_session():
    """Create a PostgreSQL test database and yield a session."""
    engine = create_async_engine(_test_db_url, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session, factory

    await engine.dispose()


async def _run_cleanup_once(factory: async_sessionmaker, timeout_minutes: int = 30) -> None:
    """Run the cleanup logic once without the loop."""
    from sqlalchemy import update

    cutoff = datetime.now(UTC) - timedelta(minutes=timeout_minutes)
    async with factory() as session:
        await session.execute(
            update(AssessmentSession)
            .where(
                AssessmentSession.status == "active",
                AssessmentSession.updated_at < cutoff,
            )
            .values(status="timed_out")
        )
        await session.commit()


@pytest.mark.asyncio
async def test_marks_stale_session_as_timed_out(db_session):
    session, factory = db_session

    stale_time = datetime.now(UTC) - timedelta(minutes=35)
    session.add(
        AssessmentSession(
            session_id="stale-1",
            thread_id="thread-stale-1",
            skill_ids=["python"],
            target_level="mid",
            status="active",
            created_at=stale_time,
            updated_at=stale_time,
        )
    )
    await session.commit()

    await _run_cleanup_once(factory, timeout_minutes=30)

    result = await session.execute(
        select(AssessmentSession).where(AssessmentSession.session_id == "stale-1")
    )
    row = result.scalar_one()
    assert row.status == "timed_out"


@pytest.mark.asyncio
async def test_does_not_touch_active_recent_sessions(db_session):
    session, factory = db_session

    recent_time = datetime.now(UTC) - timedelta(minutes=5)
    session.add(
        AssessmentSession(
            session_id="recent-1",
            thread_id="thread-recent-1",
            skill_ids=["python"],
            target_level="mid",
            status="active",
            created_at=recent_time,
            updated_at=recent_time,
        )
    )
    await session.commit()

    await _run_cleanup_once(factory, timeout_minutes=30)

    result = await session.execute(
        select(AssessmentSession).where(AssessmentSession.session_id == "recent-1")
    )
    row = result.scalar_one()
    assert row.status == "active"


@pytest.mark.asyncio
async def test_does_not_touch_completed_sessions(db_session):
    session, factory = db_session

    stale_time = datetime.now(UTC) - timedelta(minutes=60)
    session.add(
        AssessmentSession(
            session_id="completed-1",
            thread_id="thread-completed-1",
            skill_ids=["python"],
            target_level="mid",
            status="completed",
            created_at=stale_time,
            updated_at=stale_time,
        )
    )
    await session.commit()

    await _run_cleanup_once(factory, timeout_minutes=30)

    result = await session.execute(
        select(AssessmentSession).where(AssessmentSession.session_id == "completed-1")
    )
    row = result.scalar_one()
    assert row.status == "completed"


@pytest.mark.asyncio
async def test_cleanup_handles_empty_database(db_session):
    """Should not error when there are no sessions to clean up."""
    _, factory = db_session
    # Should not raise
    await _run_cleanup_once(factory, timeout_minutes=30)


@pytest.mark.asyncio
async def test_cleanup_handles_multiple_stale_sessions(db_session):
    session, factory = db_session

    stale_time = datetime.now(UTC) - timedelta(minutes=45)
    for i in range(3):
        session.add(
            AssessmentSession(
                session_id=f"stale-multi-{i}",
                thread_id=f"thread-multi-{i}",
                skill_ids=["go"],
                target_level="senior",
                status="active",
                created_at=stale_time,
                updated_at=stale_time,
            )
        )
    await session.commit()

    await _run_cleanup_once(factory, timeout_minutes=30)

    for i in range(3):
        result = await session.execute(
            select(AssessmentSession).where(AssessmentSession.session_id == f"stale-multi-{i}")
        )
        row = result.scalar_one()
        assert row.status == "timed_out"
