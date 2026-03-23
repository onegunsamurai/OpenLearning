from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict, deque
from datetime import UTC, datetime

from sqlalchemy import select

from app.agents.schemas import BloomValidatorOutput, ContentGeneratorOutput
from app.db import AssessmentResult, ConceptConfig, MaterialResult, get_db
from app.graph.content_state import (
    ContentPlan,
    ContentSection,
    GeneratedContent,
    LearningMaterial,
    LearningMaterialState,
    LearningObjective,
    PrioritizedGap,
)
from app.knowledge_base.taxonomy import (
    BLOOM_INT,
    BLOOM_LABELS,
    BLOOM_VERBS,
    TaxonomyIndex,
    get_taxonomy_index,
)
from app.prompts.content import (
    BLOOM_VALIDATOR_SYSTEM_PROMPT,
    BLOOM_VALIDATOR_USER_PROMPT,
    CONTENT_GENERATOR_SYSTEM_PROMPT,
    CONTENT_GENERATOR_USER_PROMPT,
)
from app.services.ai import ainvoke_structured

logger = logging.getLogger("openlearning.content")

# Pipeline constants
BLOOM_PASS_THRESHOLD = 0.75
QUALITY_PASS_THRESHOLD = 0.70
MAX_ITERATIONS = 3
PARALLEL_GAP_LIMIT = 5


# ---------------------------------------------------------------------------
# Node 1: Input Reader
# ---------------------------------------------------------------------------


async def input_reader(state: LearningMaterialState) -> dict:
    """Load AssessmentResult by session_id and initialize TaxonomyIndex."""
    session_id = state["session_id"]

    async for db in get_db():
        result = await db.execute(
            select(AssessmentResult).where(AssessmentResult.session_id == session_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError(f"No AssessmentResult found for session_id={session_id}")

        assessment_data = {
            "session_id": row.session_id,
            "knowledge_graph": row.knowledge_graph,
            "gap_nodes": row.gap_nodes or [],
            "learning_plan": row.learning_plan,
            "proficiency_scores": row.proficiency_scores,
        }

    # Determine domain from gap nodes or fall back
    domain = state.get("domain", "backend_engineering")
    taxonomy = get_taxonomy_index(domain)

    # Validate concept_ids exist in taxonomy
    gap_nodes = assessment_data.get("gap_nodes", [])
    for gap in gap_nodes:
        concept_id = gap.get("concept", "")
        if not taxonomy.has(concept_id):
            logger.warning(
                "Concept '%s' not found in taxonomy for domain '%s', skipping",
                concept_id,
                domain,
            )

    return {
        "assessment_result_data": assessment_data,
        "domain": domain,
    }


# ---------------------------------------------------------------------------
# Node 2: Gap Prioritizer
# ---------------------------------------------------------------------------


async def gap_prioritizer(state: LearningMaterialState) -> dict:
    """Compute priority scores for each gap and sort descending."""
    assessment_data = state["assessment_result_data"]
    domain = state.get("domain", "backend_engineering")
    taxonomy = get_taxonomy_index(domain)
    gap_nodes = assessment_data.get("gap_nodes", [])

    # Load IRT weights from DB
    irt_weights: dict[str, float] = {}
    async for db in get_db():
        concept_ids = [g.get("concept", "") for g in gap_nodes]
        if concept_ids:
            result = await db.execute(
                select(ConceptConfig).where(ConceptConfig.concept_id.in_(concept_ids))
            )
            for row in result.scalars():
                irt_weights[row.concept_id] = row.irt_weight

    prioritized: list[PrioritizedGap] = []
    for gap in gap_nodes:
        concept_id = gap.get("concept", "")
        if not taxonomy.has(concept_id):
            continue

        current_confidence = gap.get("confidence", 0.0)
        current_bloom_str = gap.get("bloom_level", "remember")
        current_bloom = BLOOM_INT.get(current_bloom_str, 1)
        target_bloom = taxonomy.bloom_target_int(concept_id)
        if target_bloom <= current_bloom:
            continue  # No bloom gap — skip
        bloom_distance = target_bloom - current_bloom
        severity = taxonomy.gap_severity(concept_id, current_confidence)
        weight = taxonomy.irt_weight(concept_id, irt_weights.get(concept_id))
        priority_score = severity * bloom_distance * weight

        evidence = gap.get("evidence", [])
        prerequisites = taxonomy.prereqs(concept_id)

        prioritized.append(
            PrioritizedGap(
                concept_id=concept_id,
                current_bloom=current_bloom,
                target_bloom=target_bloom,
                bloom_distance=bloom_distance,
                gap_severity=severity,
                irt_weight=weight,
                priority_score=priority_score,
                evidence=evidence,
                prerequisites=prerequisites,
            )
        )

    prioritized.sort(key=lambda g: g.priority_score, reverse=True)
    return {"prioritized_gaps": prioritized}


# ---------------------------------------------------------------------------
# Node 3: Objective Generator
# ---------------------------------------------------------------------------


def _topological_sort(concept_ids: list[str], taxonomy: TaxonomyIndex) -> list[str]:
    """Kahn's algorithm for topological sort based on prerequisite edges."""
    concept_set = set(concept_ids)

    # Build adjacency list and in-degree count (only within the gap set)
    in_degree: dict[str, int] = defaultdict(int)
    adjacency: dict[str, list[str]] = defaultdict(list)
    for cid in concept_ids:
        in_degree.setdefault(cid, 0)
        for prereq in taxonomy.prereqs(cid):
            if prereq in concept_set:
                adjacency[prereq].append(cid)
                in_degree[cid] += 1

    queue: deque[str] = deque(cid for cid in concept_ids if in_degree[cid] == 0)
    result: list[str] = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for dependent in adjacency[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # If cycle detected, append remaining (shouldn't happen in valid data)
    remaining = [cid for cid in concept_ids if cid not in set(result)]
    result.extend(remaining)

    return result


async def objective_generator(state: LearningMaterialState) -> dict:
    """Generate learning objectives with topological prerequisite ordering."""
    prioritized_gaps = state["prioritized_gaps"]
    domain = state.get("domain", "backend_engineering")
    taxonomy = get_taxonomy_index(domain)

    concept_ids = [g.concept_id for g in prioritized_gaps]
    prereq_order = _topological_sort(concept_ids, taxonomy)

    objectives: list[LearningObjective] = []
    for gap in prioritized_gaps:
        # Generate one objective per intermediate Bloom level
        for bloom_level in range(gap.current_bloom + 1, gap.target_bloom + 1):
            verbs = BLOOM_VERBS.get(bloom_level, ["understand"])
            verb = verbs[0]
            bloom_label = BLOOM_LABELS.get(bloom_level, "understand")
            concept_name = gap.concept_id.replace("_", " ")

            objective_text = f"{verb.capitalize()} {concept_name} at the {bloom_label} level"

            objectives.append(
                LearningObjective(
                    concept_id=gap.concept_id,
                    bloom_level=bloom_level,
                    verb=verb,
                    objective_text=objective_text,
                    prereq_concept_ids=gap.prerequisites,
                )
            )

    return {"objectives": objectives, "prereq_order": prereq_order}


# ---------------------------------------------------------------------------
# Node 4+5: Generate All Content (parallel across gaps)
# ---------------------------------------------------------------------------


async def _generate_single_content(
    gap: PrioritizedGap,
    objectives: list[LearningObjective],
    taxonomy: TaxonomyIndex,
    domain: str,
    critique: str = "",
) -> tuple[ContentPlan, GeneratedContent]:
    """Generate content for a single gap (content planning + LLM generation)."""
    # Content planning (CLT params)
    clt = taxonomy.clt_params(gap.concept_id, gap.bloom_distance)
    tier = taxonomy.level(gap.concept_id)
    target_bloom_label = BLOOM_LABELS.get(gap.target_bloom, "understand")

    format_hints = ["explanation"]
    if gap.target_bloom >= 3:  # apply or higher
        format_hints.append("code_example")
    if gap.bloom_distance > 2:
        format_hints.append("analogy")
    format_hints.append("quiz")

    evidence_anchors = gap.evidence if gap.evidence else ["No specific evidence available"]

    plan = ContentPlan(
        concept_id=gap.concept_id,
        target_bloom=gap.target_bloom,
        chunk_count=clt["chunk_count"],
        example_count=clt["example_count"],
        scaffolding_depth=clt["scaffolding_depth"],
        format_hints=format_hints,
        evidence_anchors=evidence_anchors,
    )

    # Find the highest-level objective for this concept
    concept_objectives = [o for o in objectives if o.concept_id == gap.concept_id]
    objective_text = (
        concept_objectives[-1].objective_text
        if concept_objectives
        else (f"Understand {gap.concept_id.replace('_', ' ')}")
    )

    # Build critique section
    critique_section = ""
    if critique:
        critique_section = (
            f"PREVIOUS CRITIQUE (address these issues in this version):\n{critique}\n\n"
        )

    prompt = (
        CONTENT_GENERATOR_SYSTEM_PROMPT
        + "\n\n"
        + CONTENT_GENERATOR_USER_PROMPT.format(
            concept_id=gap.concept_id,
            domain=domain,
            level_tier=tier,
            objective_text=objective_text,
            target_bloom_label=target_bloom_label,
            target_bloom_int=gap.target_bloom,
            evidence_anchors="\n".join(evidence_anchors),
            chunk_count=plan.chunk_count,
            example_count=plan.example_count,
            scaffolding_depth=plan.scaffolding_depth,
            format_hints=", ".join(format_hints),
            critique_section=critique_section,
        )
    )

    result = await ainvoke_structured(
        ContentGeneratorOutput,
        prompt,
        agent_name="content_generator",
    )

    sections = [
        ContentSection(
            type=s.type,
            title=s.title,
            body=s.body,
            code_block=s.code_block,
            answer=s.answer,
        )
        for s in result.sections
    ]

    content = GeneratedContent(
        concept_id=gap.concept_id,
        bloom_level=gap.target_bloom,
        sections=sections,
        raw_prompt=prompt,
    )

    return plan, content


async def generate_all_content(state: LearningMaterialState) -> dict:
    """Generate content for all gaps in parallel with semaphore."""
    prioritized_gaps = state["prioritized_gaps"]
    objectives = state["objectives"]
    domain = state.get("domain", "backend_engineering")
    taxonomy = get_taxonomy_index(domain)

    semaphore = asyncio.Semaphore(PARALLEL_GAP_LIMIT)

    async def generate_with_semaphore(
        gap: PrioritizedGap,
    ) -> tuple[str, ContentPlan, GeneratedContent]:
        async with semaphore:
            plan, content = await _generate_single_content(gap, objectives, taxonomy, domain)
            return gap.concept_id, plan, content

    results = await asyncio.gather(
        *(generate_with_semaphore(gap) for gap in prioritized_gaps),
        return_exceptions=True,
    )

    content_plans: dict[str, ContentPlan] = {}
    raw_content: dict[str, GeneratedContent] = {}

    for result in results:
        if isinstance(result, Exception):
            logger.error("Content generation failed: %s", result)
            continue
        concept_id, plan, content = result
        content_plans[concept_id] = plan
        raw_content[concept_id] = content

    if not raw_content and prioritized_gaps:
        raise RuntimeError(f"Content generation failed for all {len(prioritized_gaps)} gaps")

    return {"content_plans": content_plans, "raw_content": raw_content}


# ---------------------------------------------------------------------------
# Node 6+7: Validate All Content (with per-gap retry loop)
# ---------------------------------------------------------------------------


async def _validate_single_content(
    concept_id: str,
    content: GeneratedContent,
    objectives: list[LearningObjective],
    taxonomy: TaxonomyIndex,
) -> BloomValidatorOutput:
    """Run Bloom validation on generated content for a single gap."""
    target_bloom_label = BLOOM_LABELS.get(content.bloom_level, "understand")
    concept_objectives = [o for o in objectives if o.concept_id == concept_id]
    objective_text = (
        concept_objectives[-1].objective_text
        if concept_objectives
        else (f"Understand {concept_id.replace('_', ' ')}")
    )

    material_json = json.dumps([s.model_dump() for s in content.sections], indent=2)

    prompt = (
        BLOOM_VALIDATOR_SYSTEM_PROMPT
        + "\n\n"
        + BLOOM_VALIDATOR_USER_PROMPT.format(
            target_bloom_label=target_bloom_label,
            target_bloom_int=content.bloom_level,
            concept_id=concept_id,
            objective_text=objective_text,
            generated_material=material_json,
        )
    )

    return await ainvoke_structured(
        BloomValidatorOutput,
        prompt,
        agent_name="bloom_validator",
    )


async def validate_all_content(state: LearningMaterialState) -> dict:
    """Validate all generated content with per-gap retry loop and quality gate."""
    raw_content = state["raw_content"]
    prioritized_gaps = state["prioritized_gaps"]
    objectives = state["objectives"]
    domain = state.get("domain", "backend_engineering")
    taxonomy = get_taxonomy_index(domain)

    gap_map = {g.concept_id: g for g in prioritized_gaps}
    final_materials: dict[str, LearningMaterial] = {}

    for concept_id, content in raw_content.items():
        gap = gap_map.get(concept_id)
        if not gap:
            continue

        current_content = content
        iteration = 0
        critique = ""

        while True:
            iteration += 1

            validation = await _validate_single_content(
                concept_id, current_content, objectives, taxonomy
            )

            bloom_score = validation.bloom_alignment
            quality_score = (
                validation.accuracy + validation.clarity + validation.evidence_alignment
            ) / 3.0

            # Quality gate
            if bloom_score >= BLOOM_PASS_THRESHOLD and quality_score >= QUALITY_PASS_THRESHOLD:
                # PASS
                final_materials[concept_id] = LearningMaterial(
                    concept_id=concept_id,
                    target_bloom=gap.target_bloom,
                    bloom_score=bloom_score,
                    quality_score=quality_score,
                    sections=current_content.sections,
                    iteration_count=iteration,
                    generated_at=datetime.now(UTC),
                )
                break
            elif iteration >= MAX_ITERATIONS:
                # FLAG — emit with quality flag
                final_materials[concept_id] = LearningMaterial(
                    concept_id=concept_id,
                    target_bloom=gap.target_bloom,
                    bloom_score=bloom_score,
                    quality_score=quality_score,
                    sections=current_content.sections,
                    iteration_count=iteration,
                    quality_flag="max_iterations_reached",
                    generated_at=datetime.now(UTC),
                )
                logger.warning(
                    "Quality gate: max iterations reached for concept '%s' "
                    "(bloom=%.2f, quality=%.2f)",
                    concept_id,
                    bloom_score,
                    quality_score,
                )
                break
            else:
                # RETRY — regenerate with critique
                critique = validation.critique or "Improve Bloom alignment and quality."
                logger.info(
                    "Quality gate: retrying concept '%s' (iteration %d, bloom=%.2f, quality=%.2f)",
                    concept_id,
                    iteration,
                    bloom_score,
                    quality_score,
                )
                _, current_content = await _generate_single_content(
                    gap, objectives, taxonomy, domain, critique=critique
                )

    # Persist to DB
    await _persist_materials(state["session_id"], domain, final_materials)

    return {"final_materials": final_materials}


async def _persist_materials(
    session_id: str,
    domain: str,
    materials: dict[str, LearningMaterial],
) -> None:
    """Batch insert MaterialResult rows."""
    if not materials:
        return

    rows = []
    for concept_id, mat in materials.items():
        rows.append(
            MaterialResult(
                session_id=session_id,
                concept_id=concept_id,
                domain=domain,
                bloom_score=mat.bloom_score,
                quality_score=mat.quality_score,
                iteration_count=mat.iteration_count,
                quality_flag=mat.quality_flag,
                material={
                    "concept_id": mat.concept_id,
                    "target_bloom": mat.target_bloom,
                    "sections": [s.model_dump() for s in mat.sections],
                    "bloom_score": mat.bloom_score,
                    "quality_score": mat.quality_score,
                    "iteration_count": mat.iteration_count,
                },
            )
        )

    async for db in get_db():
        db.add_all(rows)
        await db.commit()
