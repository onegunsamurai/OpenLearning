from __future__ import annotations

from typing import TypedDict

from app.models.assessment_pipeline import (
    THOROUGHNESS_CAPS,
    AgendaItem,
    EvaluationResult,
    Question,
    Response,
    Thoroughness,
    TopicStatus,
)
from app.models.bloom import BLOOM_ORDER, LEVEL_BLOOM_MAP, BloomLevel, bloom_index
from app.models.enriched_gap import EnrichedGapAnalysis, EnrichedGapItem
from app.models.knowledge import KnowledgeGraph, KnowledgeNode
from app.models.pipeline_plan import LearningPhase, LearningPlan, Resource

# Re-export all symbols so existing `from app.graph.state import X` still works.
__all__ = [
    "BLOOM_ORDER",
    "LEVEL_BLOOM_MAP",
    "THOROUGHNESS_CAPS",
    "AgendaItem",
    "AssessmentState",
    "BloomLevel",
    "EnrichedGapAnalysis",
    "EnrichedGapItem",
    "EvaluationResult",
    "KnowledgeGraph",
    "KnowledgeNode",
    "LearningPhase",
    "LearningPlan",
    "Question",
    "Resource",
    "Response",
    "Thoroughness",
    "TopicStatus",
    "bloom_index",
    "make_initial_state",
]


class AssessmentState(TypedDict, total=False):
    candidate_id: str
    skill_ids: list[str]
    skill_domain: str
    target_level: str

    # Assessment loop
    question_history: list[Question]
    response_history: list[Response]
    current_topic: str
    current_bloom_level: BloomLevel
    topics_evaluated: list[str]
    questions_on_current_topic: int
    assessment_complete: bool

    # Evaluation
    latest_evaluation: EvaluationResult

    # Knowledge
    knowledge_graph: KnowledgeGraph
    target_graph: KnowledgeGraph
    gap_nodes: list[KnowledgeNode]
    enriched_gap_analysis: EnrichedGapAnalysis
    learning_plan: LearningPlan

    # Topic agenda
    topic_agenda: list[AgendaItem]
    thoroughness: Thoroughness
    max_questions_per_topic: int

    # Human-in-the-loop
    pending_question: Question | None


def make_initial_state(
    candidate_id: str,
    skill_ids: list[str],
    skill_domain: str,
    target_level: str = "mid",
    thoroughness: str = "standard",
) -> AssessmentState:
    thor = Thoroughness(thoroughness)
    return AssessmentState(
        candidate_id=candidate_id,
        skill_ids=skill_ids,
        skill_domain=skill_domain,
        target_level=target_level,
        question_history=[],
        response_history=[],
        current_topic="",
        current_bloom_level=BloomLevel.understand,
        topics_evaluated=[],
        questions_on_current_topic=0,
        assessment_complete=False,
        latest_evaluation=EvaluationResult(
            question_id="", confidence=0.0, bloom_level=BloomLevel.remember, evidence=[]
        ),
        knowledge_graph=KnowledgeGraph(),
        target_graph=KnowledgeGraph(),
        gap_nodes=[],
        enriched_gap_analysis=EnrichedGapAnalysis(overall_readiness=0, summary="", gaps=[]),
        learning_plan=LearningPlan(phases=[], total_hours=0, summary=""),
        topic_agenda=[],
        thoroughness=thor,
        max_questions_per_topic=THOROUGHNESS_CAPS[thor],
        pending_question=None,
    )
