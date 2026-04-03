from __future__ import annotations

from typing import Literal

from app.models.base import CamelModel


class EnrichedGapItem(CamelModel):
    skill_id: str
    skill_name: str
    current_level: int  # 0-100
    target_level: int  # 0-100
    gap: int  # target - current
    priority: Literal["critical", "high", "medium", "low"]
    recommendation: str


class EnrichedGapAnalysis(CamelModel):
    overall_readiness: int  # 0-100
    summary: str
    gaps: list[EnrichedGapItem]
