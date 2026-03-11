from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    skill_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    target_level: Mapped[str] = mapped_column(String(20), nullable=False, default="mid")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    result: Mapped[AssessmentResult | None] = relationship(back_populates="session")


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_sessions.session_id"), nullable=False
    )
    knowledge_graph: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    gap_nodes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    learning_plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    proficiency_scores: Mapped[list | None] = mapped_column(JSON, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[AssessmentSession] = relationship(back_populates="result")


_engine = None
_async_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def _get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(_get_engine(), expire_on_commit=False)
    return _async_session_factory


async def init_db() -> None:
    """Create data directory and all tables."""
    os.makedirs("data", exist_ok=True)
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async DB session."""
    factory = _get_session_factory()
    async with factory() as session:
        yield session
