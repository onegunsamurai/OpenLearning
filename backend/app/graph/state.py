from __future__ import annotations

from enum import StrEnum
from typing import Literal, TypedDict

from app.models.base import CamelModel


class BloomLevel(StrEnum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyze = "analyze"
    evaluate = "evaluate"
    create = "create"


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


BLOOM_ORDER: list[BloomLevel] = list(BloomLevel)

LEVEL_BLOOM_MAP: dict[str, BloomLevel] = {
    "junior": BloomLevel.understand,
    "mid": BloomLevel.apply,
    "senior": BloomLevel.analyze,
    "staff": BloomLevel.evaluate,
}


def bloom_index(level: BloomLevel) -> int:
    return BLOOM_ORDER.index(level)


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


class EnrichedGapItem(CamelModel):
    skill_id: str
    skill_name: str
    current_level: int  # 0-100
    target_level: int  # 0-100
    gap: int  # target - current
    priority: Literal["critical", "high", "medium", "low"]
    recommendation: str


class EnrichedGapAnalysis(CamelModel):
    overall_readiness: int  # 0-100
    summary: str
    gaps: list[EnrichedGapItem]


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
