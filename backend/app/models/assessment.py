from .base import CamelModel


class ProficiencyScore(CamelModel):
    skill_id: str
    skill_name: str
    score: int
    confidence: float
    reasoning: str
