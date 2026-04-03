from __future__ import annotations

from app.models.base import CamelModel


class Resource(CamelModel):
    type: str  # video, article, project, exercise
    title: str
    url: str | None = None


class LearningPhase(CamelModel):
    phase_number: int
    title: str
    concepts: list[str]
    rationale: str
    resources: list[Resource]
    estimated_hours: float


class LearningPlan(CamelModel):
    phases: list[LearningPhase]
    total_hours: float
    summary: str
