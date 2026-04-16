from __future__ import annotations

from pydantic import field_validator

from app.models.assessment import ProficiencyScore
from app.models.base import CamelModel
from app.models.gap_analysis import GapAnalysis


class AssessmentStartRequest(CamelModel):
    skill_ids: list[str]
    target_level: str = "mid"
    role_id: str | None = None
    thoroughness: str = "standard"

    @field_validator("skill_ids")
    @classmethod
    def validate_skill_ids(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ValueError("Too many skills (max 50)")
        return v

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, v: str) -> str:
        v = v.lower().strip()
        valid_levels = {"junior", "mid", "senior", "staff"}
        if v not in valid_levels:
            raise ValueError(f"Target level must be one of: {', '.join(sorted(valid_levels))}")
        return v

    @field_validator("role_id")
    @classmethod
    def validate_role_id(cls, v: str | None) -> str | None:
        from app.knowledge_base.loader import list_domains

        if v is not None and v not in list_domains():
            raise ValueError(f"Unknown role: {v}")
        return v

    @field_validator("thoroughness")
    @classmethod
    def validate_thoroughness(cls, v: str) -> str:
        if v not in ("quick", "standard", "thorough"):
            raise ValueError("Thoroughness must be one of: quick, standard, thorough")
        return v


class AssessmentStartResponse(CamelModel):
    session_id: str
    question: str
    estimated_questions: int | None = None


class AssessmentRespondRequest(CamelModel):
    response: str

    @field_validator("response")
    @classmethod
    def validate_response_length(cls, v: str) -> str:
        if len(v) > 10_000:
            raise ValueError("Response too long (max 10,000 characters)")
        return v


class KnowledgeNodeOut(CamelModel):
    concept: str
    confidence: float
    bloom_level: str
    prerequisites: list[str]


class KnowledgeGraphOut(CamelModel):
    nodes: list[KnowledgeNodeOut]


class ResourceOut(CamelModel):
    type: str
    title: str
    url: str | None = None


class ConceptOut(CamelModel):
    """A concept card rendered on the assessment report page.

    Each concept owns its own learning resources so the frontend can display
    resources per-concept without needing a separate lookup. See issue #168.
    """

    key: str
    name: str
    description: str = ""
    resources: list[ResourceOut] = []


class LearningPhaseOut(CamelModel):
    phase_number: int
    title: str
    concepts: list[ConceptOut]
    rationale: str
    estimated_hours: float


class LearningPlanOut(CamelModel):
    summary: str
    total_hours: float
    phases: list[LearningPhaseOut]


class AssessmentReportResponse(CamelModel):
    knowledge_graph: KnowledgeGraphOut
    gap_analysis: GapAnalysis
    learning_plan: LearningPlanOut
    proficiency_scores: list[ProficiencyScore]
