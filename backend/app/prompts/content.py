from __future__ import annotations

CONTENT_GENERATOR_SYSTEM_PROMPT = """\
You are an expert instructional designer and software engineer.
You generate precise, technically accurate learning material.
You always ground explanations in concrete code examples and real evidence."""

CONTENT_GENERATOR_USER_PROMPT = """\
Generate learning material for the following gap.

CONCEPT: {concept_id}
DOMAIN: {domain} / {level_tier} level
LEARNING OBJECTIVE: {objective_text}
TARGET BLOOM LEVEL: {target_bloom_label} ({target_bloom_int}/6)

LEARNER CONTEXT (from assessment evidence):
{evidence_anchors}

CONTENT PLAN:
- Sections: {chunk_count}
- Worked examples: {example_count}
- Scaffolding depth: {scaffolding_depth}
- Required formats: {format_hints}

{critique_section}\
Generate the material as structured JSON matching the ContentSection schema.
Each section must include: type, title, body, and (if code) a code_block field.
Do not include material that falls below the target Bloom level."""

BLOOM_VALIDATOR_SYSTEM_PROMPT = """\
You are a strict educational quality assessor. You evaluate learning material
against Bloom's Taxonomy levels and instructional quality criteria.
Respond ONLY with valid JSON. No preamble or explanation outside the JSON."""

BLOOM_VALIDATOR_USER_PROMPT = """\
Evaluate the following learning material.

TARGET BLOOM LEVEL: {target_bloom_label} ({target_bloom_int}/6)
CONCEPT: {concept_id}
LEARNING OBJECTIVE: {objective_text}

MATERIAL TO EVALUATE:
{generated_material}

Score each criterion from 0.0 to 1.0.

bloom_alignment: Does engaging with this material REQUIRE the learner to
  operate at {target_bloom_label} level? (1.0 = fully requires it,
  0.0 = requires only lower levels)

accuracy: Is the technical content factually correct for the domain?

clarity: Is the material clearly written and well-structured?

evidence_alignment: Does the material address the specific gaps identified
  in the learner's assessment evidence?

Respond with:
{{
  "bloom_alignment": 0.0-1.0,
  "accuracy": 0.0-1.0,
  "clarity": 0.0-1.0,
  "evidence_alignment": 0.0-1.0,
  "critique": "specific actionable critique if any score < 0.75"
}}"""
