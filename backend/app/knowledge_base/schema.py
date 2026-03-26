from __future__ import annotations

from pydantic import BaseModel, field_validator

LEVEL_ORDER: list[str] = ["junior", "mid", "senior", "staff"]


class ConceptSchema(BaseModel):
    concept: str
    display_name: str = ""
    target_confidence: float
    bloom_target: str
    prerequisites: list[str] = []


class LevelSchema(BaseModel):
    concepts: list[ConceptSchema]


class KnowledgeBaseSchema(BaseModel):
    domain: str
    display_name: str
    description: str
    mapped_skill_ids: list[str]
    levels: dict[str, LevelSchema]

    @field_validator("levels")
    @classmethod
    def must_have_all_levels(cls, v: dict) -> dict:
        required = set(LEVEL_ORDER)
        missing = required - v.keys()
        if missing:
            raise ValueError(f"Missing levels: {missing}")
        return v
