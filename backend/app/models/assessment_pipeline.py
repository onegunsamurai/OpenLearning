from __future__ import annotations

from enum import StrEnum

from app.models.base import CamelModel
from app.models.bloom import BloomLevel


class TopicStatus(StrEnum):
    pending = "pending"
    active = "active"
    assessed = "assessed"
    inferred = "inferred"
    skipped = "skipped"


class Thoroughness(StrEnum):
    quick = "quick"
    standard = "standard"
    thorough = "thorough"


THOROUGHNESS_CAPS: dict[Thoroughness, int] = {
    Thoroughness.quick: 2,
    Thoroughness.standard: 4,
    Thoroughness.thorough: 6,
}


class AgendaItem(CamelModel):
    concept: str
    level: str  # "junior", "mid", "senior", "staff"
    status: TopicStatus = TopicStatus.pending
    confidence: float = 0.0
    prerequisites: list[str] = []


class Question(CamelModel):
    id: str
    topic: str
    bloom_level: BloomLevel
    text: str
    question_type: str  # conceptual, scenario, debugging, design


class Response(CamelModel):
    question_id: str
    text: str


class EvaluationResult(CamelModel):
    question_id: str
    confidence: float  # 0.0-1.0
    bloom_level: BloomLevel
    evidence: list[str]
