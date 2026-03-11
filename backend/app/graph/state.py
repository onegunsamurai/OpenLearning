from __future__ import annotations

from enum import StrEnum
from typing import TypedDict

from app.models.base import CamelModel


class BloomLevel(StrEnum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyze = "analyze"
    evaluate = "evaluate"
    create = "create"


BLOOM_ORDER: list[BloomLevel] = list(BloomLevel)


def bloom_index(level: BloomLevel) -> int:
    return BLOOM_ORDER.index(level)


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


class KnowledgeNode(CamelModel):
    concept: str
    confidence: float  # 0.0-1.0
    bloom_level: BloomLevel
    prerequisites: list[str] = []
    evidence: list[str] = []


class KnowledgeGraph(CamelModel):
    nodes: list[KnowledgeNode] = []
    edges: list[tuple[str, str]] = []  # (prerequisite, dependent)

    def get_node(self, concept: str) -> KnowledgeNode | None:
        for node in self.nodes:
            if node.concept == concept:
                return node
        return None

    def upsert_node(self, node: KnowledgeNode) -> None:
        for i, existing in enumerate(self.nodes):
            if existing.concept == node.concept:
                self.nodes[i] = node
                return
        self.nodes.append(node)


class Resource(CamelModel):
    type: str  # video, article, project, exercise
    title: str
    url: str | None = None


class LearningPhase(CamelModel):
    phase_number: int
    title: str
    concepts: list[str]
    rationale: str
    resources: list[Resource]
    estimated_hours: float


class LearningPlan(CamelModel):
    phases: list[LearningPhase]
    total_hours: float
    summary: str


class AssessmentState(TypedDict, total=False):
    candidate_id: str
    skill_ids: list[str]
    skill_domain: str
    target_level: str

    # Calibration
    calibration_questions: list[Question]
    calibration_responses: list[Response]
    calibrated_level: str

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
    learning_plan: LearningPlan

    # Human-in-the-loop
    pending_question: Question | None


def make_initial_state(
    candidate_id: str,
    skill_ids: list[str],
    skill_domain: str,
    target_level: str = "mid",
) -> AssessmentState:
    return AssessmentState(
        candidate_id=candidate_id,
        skill_ids=skill_ids,
        skill_domain=skill_domain,
        target_level=target_level,
        calibration_questions=[],
        calibration_responses=[],
        calibrated_level="",
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
        learning_plan=LearningPlan(phases=[], total_hours=0, summary=""),
        pending_question=None,
    )
