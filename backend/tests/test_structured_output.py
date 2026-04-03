"""Tests for LLM output schemas used with with_structured_output()."""

from __future__ import annotations

from app.agents.schemas import (
    EvaluationOutput,
    PlanOutput,
    PlanPhaseOutput,
    PlanResourceOutput,
    QuestionOutput,
)


class TestQuestionOutput:
    def test_all_fields(self):
        output = QuestionOutput(
            topic="sql",
            bloom_level="apply",
            text="Write a JOIN query.",
            question_type="debugging",
        )
        assert output.topic == "sql"
        assert output.bloom_level == "apply"
        assert output.question_type == "debugging"


class TestEvaluationOutput:
    def test_all_fields(self):
        output = EvaluationOutput(
            confidence=0.85,
            bloom_level="analyze",
            evidence=["Good analysis", "Correct terminology"],
            reasoning="Strong answer",
        )
        assert output.confidence == 0.85
        assert len(output.evidence) == 2

    def test_confidence_boundary_values(self):
        low = EvaluationOutput(confidence=0.0, bloom_level="remember", evidence=[])
        high = EvaluationOutput(confidence=1.0, bloom_level="create", evidence=[])
        assert low.confidence == 0.0
        assert high.confidence == 1.0

    def test_default_reasoning(self):
        output = EvaluationOutput(confidence=0.5, bloom_level="understand", evidence=["OK"])
        assert output.reasoning == ""


class TestPlanOutput:
    def test_full_nested_structure(self):
        output = PlanOutput(
            summary="Learn backend basics.",
            total_hours=40.0,
            phases=[
                PlanPhaseOutput(
                    phase_number=1,
                    title="HTTP Fundamentals",
                    concepts=["http", "rest"],
                    rationale="Foundation first",
                    resources=[
                        PlanResourceOutput(
                            type="article", title="MDN HTTP Guide", url="https://mdn.dev"
                        ),
                        PlanResourceOutput(type="project", title="Build a REST API"),
                    ],
                    estimated_hours=10.0,
                ),
                PlanPhaseOutput(
                    phase_number=2,
                    title="Database Design",
                    concepts=["sql", "indexing"],
                    rationale="Build on HTTP knowledge",
                    resources=[
                        PlanResourceOutput(type="video", title="SQL Tutorial", url=None),
                    ],
                    estimated_hours=15.0,
                ),
            ],
        )
        assert output.total_hours == 40.0
        assert len(output.phases) == 2
        assert output.phases[0].title == "HTTP Fundamentals"
        assert len(output.phases[0].resources) == 2
        assert output.phases[0].resources[1].url is None

    def test_resource_optional_url(self):
        resource = PlanResourceOutput(type="exercise", title="Practice")
        assert resource.url is None

    def test_phase_default_rationale(self):
        phase = PlanPhaseOutput(
            phase_number=1,
            title="Basics",
            concepts=["a"],
            resources=[],
            estimated_hours=5.0,
        )
        assert phase.rationale == ""
