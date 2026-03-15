"""LLM output schemas for structured output.

These are plain BaseModel classes (no alias_generator) used exclusively with
LangChain's with_structured_output(). They define the shape the LLM must return.
Agents map these to the CamelModel state types after invocation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# --- Calibration ---


class CalibrationQuestionOutput(BaseModel):
    """Output schema for a single calibration question."""

    topic: str = Field(description="The technical concept being tested")
    text: str = Field(description="The question text")
    question_type: str = Field(
        default="conceptual",
        description="Type of question: conceptual, scenario, debugging, design",
    )


class CalibrationEvalConcept(BaseModel):
    """A single concept with confidence from calibration evaluation."""

    concept: str = Field(description="Name of the technical concept")
    confidence: float = Field(description="Confidence level from 0.0 to 1.0")
    bloom_level: str = Field(
        description="Bloom's taxonomy level: remember, understand, apply, analyze, evaluate, create"
    )


class CalibrationEvalOutput(BaseModel):
    """Output schema for calibration evaluation of 3 Q&A pairs."""

    calibrated_level: str = Field(description="Starting level: junior, mid, senior, or staff")
    initial_concepts: list[CalibrationEvalConcept] = Field(
        description="Initial confidence estimates for relevant concepts"
    )
    first_topic: str = Field(description="The best first topic to assess in depth")
    reasoning: str = Field(default="", description="Brief explanation of level determination")


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
