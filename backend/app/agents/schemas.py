"""LLM output schemas for structured output.

These are plain BaseModel classes (no alias_generator) used exclusively with
LangChain's with_structured_output(). They define the shape the LLM must return.
Agents map these to the CamelModel state types after invocation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# --- Question Generation ---


class QuestionOutput(BaseModel):
    """Output schema for assessment question generation."""

    topic: str = Field(description="The technical concept being tested")
    bloom_level: str = Field(
        description="Bloom's taxonomy level: remember, understand, apply, analyze, evaluate, create"
    )
    text: str = Field(description="The question text")
    question_type: str = Field(
        description="Type of question: conceptual, scenario, debugging, design"
    )


# --- Response Evaluation ---


class EvaluationOutput(BaseModel):
    """Output schema for evaluating a candidate's response."""

    confidence: float = Field(
        description="Confidence in candidate's mastery: 0.0 = completely wrong, 0.5 = partial, 1.0 = excellent"
    )
    bloom_level: str = Field(
        description="Bloom's taxonomy level the candidate actually demonstrated"
    )
    evidence: list[str] = Field(description="Specific observations supporting the evaluation")
    reasoning: str = Field(default="", description="Brief overall assessment")


# --- Learning Plan Generation ---


class PlanResourceOutput(BaseModel):
    """A single learning resource in a plan phase."""

    type: str = Field(description="Resource type: video, article, project, exercise")
    title: str = Field(description="Resource title")
    url: str | None = Field(default=None, description="Resource URL if available")


class PlanPhaseOutput(BaseModel):
    """A single phase in a learning plan."""

    phase_number: int = Field(description="Phase order number starting from 1")
    title: str = Field(description="Phase title")
    concepts: list[str] = Field(description="Concepts covered in this phase")
    rationale: str = Field(
        default="", description="Why these concepts are grouped and ordered this way"
    )
    resources: list[PlanResourceOutput] = Field(description="Learning resources for this phase")
    estimated_hours: float = Field(description="Estimated hours to complete this phase")


class PlanOutput(BaseModel):
    """Output schema for learning plan generation."""

    summary: str = Field(description="2-3 sentence plan overview")
    total_hours: float = Field(description="Total estimated hours for the entire plan")
    phases: list[PlanPhaseOutput] = Field(description="Ordered phases of the learning plan")


# --- Gap Enrichment ---


class GapRecommendationOutput(BaseModel):
    """A single gap recommendation from the LLM."""

    concept: str = Field(description="The concept name (must match a gap node concept)")
    recommendation: str = Field(
        description="A specific, actionable 1-sentence learning recommendation"
    )


class GapEnrichmentOutput(BaseModel):
    """Output schema for gap analysis enrichment."""

    summary: str = Field(
        description="2-3 sentence executive summary of the candidate's readiness and gaps"
    )
    recommendations: list[GapRecommendationOutput] = Field(
        description="One recommendation per gap concept"
    )


# --- Content Generation (Learning Material Pipeline) ---


class ContentSectionOutput(BaseModel):
    """Output schema for a single content section."""

    type: str = Field(description="Section type: explanation, code_example, analogy, quiz")
    title: str = Field(description="Section title")
    body: str = Field(description="Section body text (markdown)")
    code_block: str | None = Field(default=None, description="Code block content if applicable")
    answer: str | None = Field(default=None, description="Answer for quiz sections")


class ContentGeneratorOutput(BaseModel):
    """Output schema for learning content generation."""

    sections: list[ContentSectionOutput] = Field(description="Generated content sections")


class BloomValidatorOutput(BaseModel):
    """Output schema for Bloom taxonomy validation of generated content."""

    bloom_alignment: float = Field(
        description="Does engaging with this material require the learner to operate at the target Bloom level? (0.0-1.0)"
    )
    accuracy: float = Field(description="Is the technical content factually correct? (0.0-1.0)")
    clarity: float = Field(
        description="Is the material clearly written and well-structured? (0.0-1.0)"
    )
    evidence_alignment: float = Field(
        description="Does the material address the specific gaps from assessment evidence? (0.0-1.0)"
    )
    critique: str = Field(
        default="",
        description="Specific actionable critique if any score is below 0.75",
    )


# --- Standalone Gap Analysis (used by /api/gap-analysis route) ---


class GapAnalysisItemOutput(BaseModel):
    """A single skill gap in a gap analysis."""

    skill_id: str = Field(description="Unique identifier for the skill")
    skill_name: str = Field(description="Human-readable skill name")
    current_level: int = Field(description="Assessed proficiency score (0-100)")
    target_level: int = Field(
        description="Recommended proficiency target for a competent professional (typically 70-90)"
    )
    gap: int = Field(description="Difference: target_level - current_level, minimum 0")
    priority: Literal["critical", "high", "medium", "low"] = Field(
        description='Priority: "critical" (gap > 40), "high" (gap > 25), "medium" (gap > 10), "low" (gap <= 10)'
    )
    recommendation: str = Field(description="Specific 1-sentence action item")


class GapAnalysisOutput(BaseModel):
    """Output schema for standalone gap analysis generation."""

    overall_readiness: int = Field(
        description="Weighted average of (current_level / target_level) * 100 across all skills, rounded to nearest integer (0-100)"
    )
    summary: str = Field(description="2-3 sentence executive summary of the candidate's readiness")
    gaps: list[GapAnalysisItemOutput] = Field(
        description="Skill gaps sorted by priority (critical first) then by gap size (largest first)"
    )


# --- Standalone Learning Plan (used by /api/learning-plan route) ---


class LearningPlanModuleOutput(BaseModel):
    """A single learning module in a standalone learning plan phase."""

    id: str = Field(description="Unique module identifier (e.g. mod-1)")
    title: str = Field(description="Module title")
    description: str = Field(description="What the learner will do")
    type: Literal["theory", "quiz", "lab"] = Field(
        description='Module type: "theory" (reading/video), "quiz" (practice problems), "lab" (hands-on project)'
    )
    phase: int = Field(description="Phase number this module belongs to")
    skill_ids: list[str] = Field(description="Skill IDs addressed by this module")
    duration_hours: int = Field(description="Estimated hours to complete")
    objectives: list[str] = Field(description="Specific learning objectives")
    resources: list[str] = Field(description="Learning resources (docs, courses, books)")


class LearningPlanPhaseOutput(BaseModel):
    """A single phase in a standalone learning plan."""

    phase: int = Field(description="Phase order number starting from 1")
    name: str = Field(description="Phase name")
    description: str = Field(description="Phase description")
    modules: list[LearningPlanModuleOutput] = Field(description="Modules in this phase")


class LearningPlanOutput(BaseModel):
    """Output schema for standalone learning plan generation."""

    title: str = Field(description="Learning plan title")
    summary: str = Field(description="2-3 sentence plan overview")
    total_hours: int = Field(description="Total estimated hours for the entire plan (40-80)")
    total_weeks: int = Field(description="Total estimated weeks (4-12)")
    phases: list[LearningPlanPhaseOutput] = Field(
        description="3-4 phases ordered by dependency and priority"
    )
