from __future__ import annotations

from datetime import datetime

from app.models.base import CamelModel


class MaterialOut(CamelModel):
    concept_id: str
    domain: str
    bloom_score: float
    quality_score: float
    iteration_count: int
    quality_flag: str | None = None
    material: dict
    generated_at: datetime


class MaterialsResponse(CamelModel):
    session_id: str
    materials: list[MaterialOut]
