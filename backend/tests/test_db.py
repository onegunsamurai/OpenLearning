"""Tests for the database module."""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import AssessmentResult, AssessmentSession, Base
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
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_init_db_creates_tables(db_session: AsyncSession):
    """Tables should exist after create_all (via fixture)."""
    # If we can query without error, tables exist
    result = await db_session.execute(select(AssessmentSession))
    assert result.all() == []

    result = await db_session.execute(select(AssessmentResult))
    assert result.all() == []


@pytest.mark.asyncio
async def test_create_and_retrieve_session(db_session: AsyncSession):
    session = AssessmentSession(
        session_id="sess-1",
        thread_id="thread-1",
        skill_ids=["python", "sql"],
        target_level="mid",
        status="active",
    )
    db_session.add(session)
    await db_session.commit()

    result = await db_session.execute(
        select(AssessmentSession).where(AssessmentSession.session_id == "sess-1")
    )
    row = result.scalar_one()
    assert row.thread_id == "thread-1"
    assert row.skill_ids == ["python", "sql"]
    assert row.target_level == "mid"
    assert row.status == "active"


@pytest.mark.asyncio
async def test_session_not_found_returns_none(db_session: AsyncSession):
    result = await db_session.execute(
        select(AssessmentSession).where(AssessmentSession.session_id == "nonexistent")
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_create_assessment_result(db_session: AsyncSession):
    # Create parent session first
    db_session.add(
        AssessmentSession(
            session_id="sess-2",
            thread_id="thread-2",
            skill_ids=["react"],
            target_level="senior",
            status="active",
        )
    )
    await db_session.commit()

    db_session.add(
        AssessmentResult(
            session_id="sess-2",
            knowledge_graph={"nodes": []},
            gap_nodes=[],
            learning_plan={"summary": "test plan", "phases": []},
            proficiency_scores=[{"skill_id": "react", "score": 80}],
        )
    )
    await db_session.commit()

    result = await db_session.execute(
        select(AssessmentResult).where(AssessmentResult.session_id == "sess-2")
    )
    row = result.scalar_one()
    assert row.knowledge_graph == {"nodes": []}
    assert row.proficiency_scores == [{"skill_id": "react", "score": 80}]


@pytest.mark.asyncio
async def test_session_status_update(db_session: AsyncSession):
    db_session.add(
        AssessmentSession(
            session_id="sess-3",
            thread_id="thread-3",
            skill_ids=["go"],
            target_level="mid",
            status="active",
        )
    )
    await db_session.commit()

    row = await db_session.get(AssessmentSession, "sess-3")
    assert row is not None
    row.status = "completed"
    await db_session.commit()

    refreshed = await db_session.get(AssessmentSession, "sess-3")
    assert refreshed is not None
    assert refreshed.status == "completed"
