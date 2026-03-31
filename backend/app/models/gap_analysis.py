from __future__ import annotations

from typing import Literal

from .assessment import ProficiencyScore
from .base import CamelModel


class GapItem(CamelModel):
    skill_id: str
    skill_name: str
    current_level: int
    target_level: int
    gap: int
    priority: Literal["critical", "high", "medium", "low"]
    recommendation: str


class GapAnalysis(CamelModel):
    overall_readiness: int
    summary: str
    gaps: list[GapItem]


class GapAnalysisRequest(CamelModel):
    proficiency_scores: list[ProficiencyScore]
