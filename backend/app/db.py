from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    encrypted_api_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    sessions: Mapped[list[AssessmentSession]] = relationship(back_populates="user")
    auth_methods: Mapped[list[AuthMethod]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthMethod(Base):
    __tablename__ = "auth_methods"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_id: Mapped[str] = mapped_column(String(320), nullable=False)
    credential: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="auth_methods")

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_auth_methods_provider_id"),
    )


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    thread_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    skill_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    target_level: Mapped[str] = mapped_column(String(20), nullable=False, default="mid")
    role_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="sessions")
    result: Mapped[AssessmentResult | None] = relationship(back_populates="session")

    __table_args__ = (Index("ix_assessment_sessions_user_created", "user_id", "created_at"),)


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_sessions.session_id"), nullable=False
    )
    knowledge_graph: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    gap_nodes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    learning_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    proficiency_scores: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    enriched_gap_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[AssessmentSession] = relationship(back_populates="result")


class ConceptConfig(Base):
    __tablename__ = "concept_config"

    concept_id: Mapped[str] = mapped_column(String, primary_key=True)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    irt_weight: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class MaterialResult(Base):
    __tablename__ = "material_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("assessment_sessions.session_id"), nullable=False
    )
    concept_id: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    bloom_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    iteration_count: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_flag: Mapped[str | None] = mapped_column(String, nullable=True)
    material: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("session_id", "concept_id", name="uq_material_session_concept"),
    )


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
    """Create all tables."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async DB session."""
    factory = _get_session_factory()
    async with factory() as session:
        yield session
