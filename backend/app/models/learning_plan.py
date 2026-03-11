from typing import Literal

from .base import CamelModel
from .gap_analysis import GapAnalysis


class LearningModule(CamelModel):
    id: str
    title: str
    description: str
    type: Literal["theory", "quiz", "lab"]
    phase: int
    skill_ids: list[str]
    duration_hours: int
    objectives: list[str]
    resources: list[str]


class Phase(CamelModel):
    phase: int
    name: str
    description: str
    modules: list[LearningModule]


class LearningPlan(CamelModel):
    title: str
    summary: str
    total_hours: int
    total_weeks: int
    phases: list[Phase]


class LearningPlanRequest(CamelModel):
    gap_analysis: GapAnalysis
