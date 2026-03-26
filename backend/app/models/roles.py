from __future__ import annotations

from app.models.base import CamelModel


class RoleLevelSummary(CamelModel):
    name: str
    concept_count: int


class RoleSummary(CamelModel):
    id: str
    name: str
    description: str
    skill_count: int
    levels: list[str]


class RoleDetail(CamelModel):
    id: str
    name: str
    description: str
    mapped_skill_ids: list[str]
    levels: list[RoleLevelSummary]


class ConceptSummary(CamelModel):
    id: str
    display_name: str
    level: str
    prerequisites: list[str] = []


class RoleConceptsResponse(CamelModel):
    concepts: list[ConceptSummary]
