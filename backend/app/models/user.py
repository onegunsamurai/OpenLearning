from __future__ import annotations

from datetime import datetime

from app.models.base import CamelModel


class UserAssessmentSummary(CamelModel):
    session_id: str
    status: str
    skill_ids: list[str]
    target_level: str
    role_id: str | None = None
    role_name: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    overall_readiness: int | None = None
    skill_count: int
