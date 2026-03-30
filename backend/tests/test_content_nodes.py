from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.content_nodes import (
    MAX_ITERATIONS,
    gap_prioritizer,
    generate_all_content,
    input_reader,
    objective_generator,
    validate_all_content,
)
from app.agents.schemas import BloomValidatorOutput, ContentGeneratorOutput, ContentSectionOutput
from app.graph.content_state import (
    ContentSection,
    GeneratedContent,
    LearningMaterialState,
    PrioritizedGap,
)
from app.knowledge_base.taxonomy import clear_taxonomy_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_taxonomy_cache()
    yield
    clear_taxonomy_cache()


@pytest.fixture
def sample_gap_nodes() -> list[dict]:
    return [
        {
            "concept": "http_fundamentals",
            "confidence": 0.3,
            "bloom_level": "remember",
            "prerequisites": [],
            "evidence": ["Partial understanding of HTTP methods"],
        },
        {
            "concept": "rest_api_basics",
            "confidence": 0.2,
            "bloom_level": "remember",
            "prerequisites": ["http_fundamentals"],
            "evidence": ["Could not explain REST principles"],
        },
    ]


@pytest.fixture
def sample_assessment_data(sample_gap_nodes: list[dict]) -> dict:
    return {
        "session_id": "sess-test",
        "knowledge_graph": {"nodes": [], "edges": []},
        "gap_nodes": sample_gap_nodes,
        "learning_plan": None,
        "proficiency_scores": [],
    }


@pytest.fixture
def prioritized_gaps() -> list[PrioritizedGap]:
    return [
        PrioritizedGap(
            concept_id="http_fundamentals",
            current_bloom=1,
            target_bloom=2,
            bloom_distance=1,
            gap_severity=0.4,
            irt_weight=0.9,
            priority_score=0.36,
            evidence=["Partial understanding of HTTP methods"],
            prerequisites=[],
        ),
        PrioritizedGap(
            concept_id="rest_api_basics",
            current_bloom=1,
            target_bloom=3,
            bloom_distance=2,
            gap_severity=0.5,
            irt_weight=0.9,
            priority_score=0.9,
            evidence=["Could not explain REST principles"],
            prerequisites=["http_fundamentals"],
        ),
    ]


def _mock_content_output() -> ContentGeneratorOutput:
    return ContentGeneratorOutput(
        sections=[
            ContentSectionOutput(
                type="explanation",
                title="Understanding HTTP",
                body="HTTP is a protocol...",
            ),
            ContentSectionOutput(
                type="quiz",
                title="Check your understanding",
                body="What is the difference between GET and POST?",
                answer="GET retrieves data, POST sends data.",
            ),
        ]
    )


def _mock_validator_output(
    bloom: float = 0.9, accuracy: float = 0.9, clarity: float = 0.9, evidence: float = 0.9
) -> BloomValidatorOutput:
    return BloomValidatorOutput(
        bloom_alignment=bloom,
        accuracy=accuracy,
        clarity=clarity,
        evidence_alignment=evidence,
        critique="" if bloom >= 0.75 else "Needs improvement in Bloom alignment.",
    )


# ---------------------------------------------------------------------------
# Input Reader Tests
# ---------------------------------------------------------------------------


class TestInputReader:
    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    async def test_loads_assessment_result(
        self, mock_get_db: AsyncMock, setup_db, sample_assessment_data: dict
    ) -> None:
        from tests.conftest import _override_get_db, _TestSessionFactory, seed_result, seed_session

        mock_get_db.side_effect = _override_get_db

        async with _TestSessionFactory() as db:
            await seed_session(db, "sess-test", "thread-test", "completed")
            await seed_result(
                db,
                "sess-test",
                gap_nodes=sample_assessment_data["gap_nodes"],
            )

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
        }
        result = await input_reader(state)

        assert "assessment_result_data" in result
        assert result["assessment_result_data"]["session_id"] == "sess-test"

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    async def test_raises_on_missing_session(self, mock_get_db: AsyncMock, setup_db) -> None:
        from tests.conftest import _override_get_db

        mock_get_db.side_effect = _override_get_db

        state: LearningMaterialState = {
            "session_id": "nonexistent",
            "domain": "backend_engineering",
        }
        with pytest.raises(ValueError, match="No AssessmentResult found"):
            await input_reader(state)


# ---------------------------------------------------------------------------
# Gap Prioritizer Tests
# ---------------------------------------------------------------------------


class TestGapPrioritizer:
    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    async def test_computes_priority_scores(
        self, mock_get_db: AsyncMock, setup_db, sample_assessment_data: dict
    ) -> None:
        from tests.conftest import _override_get_db

        mock_get_db.side_effect = _override_get_db

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "assessment_result_data": sample_assessment_data,
        }
        result = await gap_prioritizer(state)
        gaps = result["prioritized_gaps"]

        assert len(gaps) == 2
        for gap in gaps:
            assert gap.priority_score > 0

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    async def test_sorts_descending(
        self, mock_get_db: AsyncMock, setup_db, sample_assessment_data: dict
    ) -> None:
        from tests.conftest import _override_get_db

        mock_get_db.side_effect = _override_get_db

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "assessment_result_data": sample_assessment_data,
        }
        result = await gap_prioritizer(state)
        gaps = result["prioritized_gaps"]

        scores = [g.priority_score for g in gaps]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    async def test_uses_assessed_bloom_from_knowledge_graph(
        self, mock_get_db: AsyncMock, setup_db
    ) -> None:
        """Gap nodes store TARGET bloom; prioritizer must read CURRENT bloom from knowledge_graph."""
        from tests.conftest import _override_get_db

        mock_get_db.side_effect = _override_get_db

        # gap_nodes has bloom_level="understand" (the TARGET, as gap_analyzer stores it)
        # knowledge_graph has the concept assessed at bloom_level="remember" (CURRENT)
        # taxonomy target for http_fundamentals is "understand" (2)
        # So bloom distance should be 2 - 1 = 1, and the gap should be included.
        assessment_data = {
            "session_id": "sess-test",
            "knowledge_graph": {
                "nodes": [
                    {
                        "concept": "http_fundamentals",
                        "confidence": 0.3,
                        "bloom_level": "remember",
                        "prerequisites": [],
                        "evidence": [],
                    },
                ],
                "edges": [],
            },
            "gap_nodes": [
                {
                    "concept": "http_fundamentals",
                    "confidence": 0.3,
                    "bloom_level": "understand",  # TARGET bloom, not current
                    "prerequisites": [],
                    "evidence": ["Partial understanding"],
                },
            ],
            "learning_plan": None,
            "proficiency_scores": [],
        }

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "assessment_result_data": assessment_data,
        }
        result = await gap_prioritizer(state)
        gaps = result["prioritized_gaps"]

        assert len(gaps) == 1
        assert gaps[0].concept_id == "http_fundamentals"
        assert gaps[0].current_bloom == 1  # remember
        assert gaps[0].target_bloom == 2  # understand
        assert gaps[0].bloom_distance == 1

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    async def test_skips_when_assessed_bloom_meets_target(
        self, mock_get_db: AsyncMock, setup_db
    ) -> None:
        """When the candidate's assessed bloom meets the taxonomy target, skip the gap."""
        from tests.conftest import _override_get_db

        mock_get_db.side_effect = _override_get_db

        # knowledge_graph shows candidate already at "understand" for http_fundamentals
        # taxonomy target for http_fundamentals is also "understand" (2)
        # So target_bloom <= current_bloom → correctly skip
        assessment_data = {
            "session_id": "sess-test",
            "knowledge_graph": {
                "nodes": [
                    {
                        "concept": "http_fundamentals",
                        "confidence": 0.3,
                        "bloom_level": "understand",
                        "prerequisites": [],
                        "evidence": [],
                    },
                ],
                "edges": [],
            },
            "gap_nodes": [
                {
                    "concept": "http_fundamentals",
                    "confidence": 0.3,
                    "bloom_level": "understand",
                    "prerequisites": [],
                    "evidence": [],
                },
            ],
            "learning_plan": None,
            "proficiency_scores": [],
        }

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "assessment_result_data": assessment_data,
        }
        result = await gap_prioritizer(state)
        gaps = result["prioritized_gaps"]

        assert len(gaps) == 0

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.get_db")
    async def test_defaults_to_remember_for_unassessed_concepts(
        self, mock_get_db: AsyncMock, setup_db
    ) -> None:
        """Un-assessed concepts (not in knowledge_graph) default to 'remember' bloom level."""
        from tests.conftest import _override_get_db

        mock_get_db.side_effect = _override_get_db

        # knowledge_graph has NO entry for http_fundamentals
        # Should default current bloom to "remember" (1); taxonomy target is "understand" (2)
        assessment_data = {
            "session_id": "sess-test",
            "knowledge_graph": {"nodes": [], "edges": []},
            "gap_nodes": [
                {
                    "concept": "http_fundamentals",
                    "confidence": 0.0,
                    "bloom_level": "understand",  # TARGET bloom
                    "prerequisites": [],
                    "evidence": [],
                },
            ],
            "learning_plan": None,
            "proficiency_scores": [],
        }

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "assessment_result_data": assessment_data,
        }
        result = await gap_prioritizer(state)
        gaps = result["prioritized_gaps"]

        assert len(gaps) == 1
        assert gaps[0].current_bloom == 1  # defaulted to remember


# ---------------------------------------------------------------------------
# Objective Generator Tests
# ---------------------------------------------------------------------------


class TestObjectiveGenerator:
    @pytest.mark.asyncio
    async def test_topological_sort(self, prioritized_gaps: list[PrioritizedGap]) -> None:
        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": prioritized_gaps,
        }
        result = await objective_generator(state)

        prereq_order = result["prereq_order"]
        assert prereq_order.index("http_fundamentals") < prereq_order.index("rest_api_basics")

    @pytest.mark.asyncio
    async def test_bloom_verb_selection(self, prioritized_gaps: list[PrioritizedGap]) -> None:
        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": prioritized_gaps,
        }
        result = await objective_generator(state)

        objectives = result["objectives"]
        assert len(objectives) > 0
        for obj in objectives:
            assert obj.verb != ""
            assert obj.objective_text != ""

    @pytest.mark.asyncio
    async def test_intermediate_objectives(self, prioritized_gaps: list[PrioritizedGap]) -> None:
        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": prioritized_gaps,
        }
        result = await objective_generator(state)

        # rest_api_basics gap spans remember(1) → apply(3), should produce 2 objectives (understand, apply)
        rest_objectives = [o for o in result["objectives"] if o.concept_id == "rest_api_basics"]
        assert len(rest_objectives) == 2
        assert rest_objectives[0].bloom_level == 2  # understand
        assert rest_objectives[1].bloom_level == 3  # apply


# ---------------------------------------------------------------------------
# Generate All Content Tests
# ---------------------------------------------------------------------------


class TestGenerateAllContent:
    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.ainvoke_structured")
    async def test_generates_for_all_gaps(
        self,
        mock_ainvoke: AsyncMock,
        prioritized_gaps: list[PrioritizedGap],
    ) -> None:
        mock_ainvoke.return_value = _mock_content_output()

        from app.graph.content_state import LearningObjective

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": prioritized_gaps,
            "objectives": [
                LearningObjective(
                    concept_id="http_fundamentals",
                    bloom_level=2,
                    verb="explain",
                    objective_text="Explain HTTP fundamentals",
                    prereq_concept_ids=[],
                ),
                LearningObjective(
                    concept_id="rest_api_basics",
                    bloom_level=3,
                    verb="implement",
                    objective_text="Implement REST API basics",
                    prereq_concept_ids=["http_fundamentals"],
                ),
            ],
        }

        result = await generate_all_content(state)

        assert "raw_content" in result
        assert "content_plans" in result
        assert len(result["raw_content"]) == 2
        assert mock_ainvoke.call_count == 2

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.ainvoke_structured")
    async def test_includes_evidence_anchors(
        self,
        mock_ainvoke: AsyncMock,
        prioritized_gaps: list[PrioritizedGap],
    ) -> None:
        mock_ainvoke.return_value = _mock_content_output()

        from app.graph.content_state import LearningObjective

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": [prioritized_gaps[0]],  # Just http_fundamentals
            "objectives": [
                LearningObjective(
                    concept_id="http_fundamentals",
                    bloom_level=2,
                    verb="explain",
                    objective_text="Explain HTTP fundamentals",
                    prereq_concept_ids=[],
                ),
            ],
        }

        await generate_all_content(state)

        # Verify the prompt passed to ainvoke contains evidence
        call_args = mock_ainvoke.call_args
        prompt = call_args[0][1]
        assert "Partial understanding of HTTP methods" in prompt

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes.ainvoke_structured")
    async def test_raises_when_all_gaps_fail(
        self,
        mock_ainvoke: AsyncMock,
        prioritized_gaps: list[PrioritizedGap],
    ) -> None:
        mock_ainvoke.side_effect = RuntimeError("LLM call failed")

        from app.graph.content_state import LearningObjective

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": prioritized_gaps,
            "objectives": [
                LearningObjective(
                    concept_id="http_fundamentals",
                    bloom_level=2,
                    verb="explain",
                    objective_text="Explain HTTP fundamentals",
                    prereq_concept_ids=[],
                ),
            ],
        }

        with pytest.raises(RuntimeError, match="Content generation failed for all"):
            await generate_all_content(state)


# ---------------------------------------------------------------------------
# Quality Gate Retry Tests
# ---------------------------------------------------------------------------


class TestQualityGateRetry:
    @pytest.mark.asyncio
    @patch("app.agents.content_nodes._persist_materials")
    @patch("app.agents.content_nodes.ainvoke_structured")
    async def test_pass_on_first_attempt(
        self,
        mock_ainvoke: AsyncMock,
        mock_persist: AsyncMock,
        prioritized_gaps: list[PrioritizedGap],
    ) -> None:
        # Validator returns passing scores
        mock_ainvoke.return_value = _mock_validator_output(bloom=0.9, accuracy=0.9)

        from app.graph.content_state import LearningObjective

        raw_content = {
            "http_fundamentals": GeneratedContent(
                concept_id="http_fundamentals",
                bloom_level=2,
                sections=[
                    ContentSection(type="explanation", title="HTTP", body="explanation text")
                ],
                raw_prompt="test prompt",
            ),
        }

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": [prioritized_gaps[0]],
            "objectives": [
                LearningObjective(
                    concept_id="http_fundamentals",
                    bloom_level=2,
                    verb="explain",
                    objective_text="Explain HTTP fundamentals",
                    prereq_concept_ids=[],
                ),
            ],
            "raw_content": raw_content,
        }

        result = await validate_all_content(state)

        materials = result["final_materials"]
        assert "http_fundamentals" in materials
        assert materials["http_fundamentals"].iteration_count == 1
        assert materials["http_fundamentals"].quality_flag is None

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes._persist_materials")
    @patch("app.agents.content_nodes._generate_single_content")
    @patch("app.agents.content_nodes._validate_single_content")
    async def test_pass_on_retry(
        self,
        mock_validate: AsyncMock,
        mock_generate: AsyncMock,
        mock_persist: AsyncMock,
        prioritized_gaps: list[PrioritizedGap],
    ) -> None:
        # First validation fails, second passes
        mock_validate.side_effect = [
            _mock_validator_output(bloom=0.5, accuracy=0.5),
            _mock_validator_output(bloom=0.9, accuracy=0.9),
        ]

        # Regenerated content
        regenerated = GeneratedContent(
            concept_id="http_fundamentals",
            bloom_level=2,
            sections=[
                ContentSection(type="explanation", title="Better HTTP", body="improved text")
            ],
            raw_prompt="test prompt v2",
        )
        mock_generate.return_value = (None, regenerated)

        from app.graph.content_state import LearningObjective

        raw_content = {
            "http_fundamentals": GeneratedContent(
                concept_id="http_fundamentals",
                bloom_level=2,
                sections=[
                    ContentSection(type="explanation", title="HTTP", body="explanation text")
                ],
                raw_prompt="test prompt",
            ),
        }

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": [prioritized_gaps[0]],
            "objectives": [
                LearningObjective(
                    concept_id="http_fundamentals",
                    bloom_level=2,
                    verb="explain",
                    objective_text="Explain HTTP fundamentals",
                    prereq_concept_ids=[],
                ),
            ],
            "raw_content": raw_content,
        }

        result = await validate_all_content(state)

        materials = result["final_materials"]
        assert materials["http_fundamentals"].iteration_count == 2
        assert materials["http_fundamentals"].quality_flag is None

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes._persist_materials")
    @patch("app.agents.content_nodes._generate_single_content")
    @patch("app.agents.content_nodes._validate_single_content")
    async def test_max_iterations_flag(
        self,
        mock_validate: AsyncMock,
        mock_generate: AsyncMock,
        mock_persist: AsyncMock,
        prioritized_gaps: list[PrioritizedGap],
    ) -> None:
        # All validations fail
        mock_validate.return_value = _mock_validator_output(bloom=0.4, accuracy=0.4)

        regenerated = GeneratedContent(
            concept_id="http_fundamentals",
            bloom_level=2,
            sections=[ContentSection(type="explanation", title="HTTP", body="text")],
            raw_prompt="test prompt",
        )
        mock_generate.return_value = (None, regenerated)

        from app.graph.content_state import LearningObjective

        raw_content = {
            "http_fundamentals": GeneratedContent(
                concept_id="http_fundamentals",
                bloom_level=2,
                sections=[ContentSection(type="explanation", title="HTTP", body="text")],
                raw_prompt="test prompt",
            ),
        }

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": [prioritized_gaps[0]],
            "objectives": [
                LearningObjective(
                    concept_id="http_fundamentals",
                    bloom_level=2,
                    verb="explain",
                    objective_text="Explain HTTP fundamentals",
                    prereq_concept_ids=[],
                ),
            ],
            "raw_content": raw_content,
        }

        result = await validate_all_content(state)

        materials = result["final_materials"]
        assert materials["http_fundamentals"].iteration_count == MAX_ITERATIONS
        assert materials["http_fundamentals"].quality_flag == "max_iterations_reached"

    @pytest.mark.asyncio
    @patch("app.agents.content_nodes._persist_materials")
    @patch("app.agents.content_nodes._generate_single_content")
    @patch("app.agents.content_nodes._validate_single_content")
    async def test_critique_propagation(
        self,
        mock_validate: AsyncMock,
        mock_generate: AsyncMock,
        mock_persist: AsyncMock,
        prioritized_gaps: list[PrioritizedGap],
    ) -> None:
        # First validation fails with critique, second passes
        mock_validate.side_effect = [
            BloomValidatorOutput(
                bloom_alignment=0.5,
                accuracy=0.5,
                clarity=0.5,
                evidence_alignment=0.5,
                critique="Material only covers Remember level, needs Apply-level exercises.",
            ),
            _mock_validator_output(bloom=0.9, accuracy=0.9),
        ]

        regenerated = GeneratedContent(
            concept_id="http_fundamentals",
            bloom_level=2,
            sections=[ContentSection(type="explanation", title="Better HTTP", body="improved")],
            raw_prompt="test prompt v2",
        )
        mock_generate.return_value = (None, regenerated)

        from app.graph.content_state import LearningObjective

        raw_content = {
            "http_fundamentals": GeneratedContent(
                concept_id="http_fundamentals",
                bloom_level=2,
                sections=[ContentSection(type="explanation", title="HTTP", body="text")],
                raw_prompt="test prompt",
            ),
        }

        state: LearningMaterialState = {
            "session_id": "sess-test",
            "domain": "backend_engineering",
            "prioritized_gaps": [prioritized_gaps[0]],
            "objectives": [
                LearningObjective(
                    concept_id="http_fundamentals",
                    bloom_level=2,
                    verb="explain",
                    objective_text="Explain HTTP fundamentals",
                    prereq_concept_ids=[],
                ),
            ],
            "raw_content": raw_content,
        }

        await validate_all_content(state)

        # Verify critique was passed to regeneration
        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args
        assert "Material only covers Remember level" in call_kwargs[1]["critique"]
