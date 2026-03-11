from typing import Literal

from .base import CamelModel


class Message(CamelModel):
    role: Literal["user", "assistant"]
    content: str


class ProficiencyScore(CamelModel):
    skill_id: str
    skill_name: str
    score: int
    confidence: float
    reasoning: str


class AssessRequest(CamelModel):
    messages: list[Message]
    skill_names: list[str]
