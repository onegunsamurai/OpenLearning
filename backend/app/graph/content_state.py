from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel


class ContentSection(BaseModel):
    type: str  # 'explanation', 'code_example', 'analogy', 'quiz'
    title: str
    body: str
    code_block: str | None = None
    answer: str | None = None


class PrioritizedGap(BaseModel):
    concept_id: str
    current_bloom: int  # 1-6
    target_bloom: int  # 1-6
    bloom_distance: int  # target - current
    gap_severity: float  # target_confidence - current_confidence
    irt_weight: float  # from concept_config table
    priority_score: float  # gap_severity * bloom_distance * irt_weight
    evidence: list[str]
    prerequisites: list[str]


class LearningObjective(BaseModel):
    concept_id: str
    bloom_level: int
    verb: str  # Bloom action verb for this level
    objective_text: str
    prereq_concept_ids: list[str]


class ContentPlan(BaseModel):
    concept_id: str
    target_bloom: int
    chunk_count: int
    example_count: int
    scaffolding_depth: str  # 'high' | 'medium' | 'low'
    format_hints: list[str]
    evidence_anchors: list[str]


class GeneratedContent(BaseModel):
    concept_id: str
    bloom_level: int
    sections: list[ContentSection]
    raw_prompt: str


class LearningMaterial(BaseModel):
    concept_id: str
    target_bloom: int
    bloom_score: float
    quality_score: float
    sections: list[ContentSection]
    iteration_count: int
    quality_flag: str | None = None
    generated_at: datetime


class LearningMaterialState(TypedDict, total=False):
    # Input
    session_id: str
    domain: str
    assessment_result_data: dict  # Raw AssessmentResult row data

    # Node 2: Gap Prioritizer
    prioritized_gaps: list[PrioritizedGap]

    # Node 3: Objective Generator
    objectives: list[LearningObjective]
    prereq_order: list[str]  # topologically sorted concept_ids

    # Node 4+5: Content Generation
    content_plans: dict[str, ContentPlan]
    raw_content: dict[str, GeneratedContent]

    # Node 6+7: Validation & Quality Gate
    final_materials: dict[str, LearningMaterial]
