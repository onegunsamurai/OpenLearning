"""Integration tests: build_assessment_markdown → materials rendering pipeline.

These tests exercise the full materials render path end-to-end — all four
section types, quality_flag rendering, tilde fencing, URL safety, and
malformed-input resilience — in a single call to build_assessment_markdown.
Each test confirms output from multiple cooperating code paths rather than
a single isolated branch.
"""

from __future__ import annotations

from datetime import datetime

from app.routes.export_utils import build_assessment_markdown

# ── Shared fixtures ──────────────────────────────────────────────────────


def _make_material(
    concept_id: str,
    sections: list[dict],
    quality_score: float = 0.85,
    bloom_score: float = 0.8,
    quality_flag: str | None = None,
) -> dict:
    return {
        "concept_id": concept_id,
        "quality_score": quality_score,
        "bloom_score": bloom_score,
        "quality_flag": quality_flag,
        "material": {"sections": sections},
    }


ALL_FOUR_SECTION_TYPES = [
    {
        "type": "explanation",
        "title": "What is HTTP/2?",
        "body": "HTTP/2 is a revision of the HTTP protocol.",
    },
    {
        "type": "code_example",
        "title": "HTTP/2 push example",
        "body": "Below is a server push fragment:",
        "code_block": "PUSH_PROMISE /styles.css",
    },
    {
        "type": "analogy",
        "title": "Like a highway fast lane",
        "body": "Multiplexing lets streams share one connection.",
    },
    {
        "type": "quiz",
        "title": "Why is HTTP/2 faster?",
        "body": "Select the correct reason.",
        "answer": "Header compression and stream multiplexing.",
    },
]


# ── Test class ────────────────────────────────────────────────────────────


class TestMaterialsExportIntegration:
    """Full render-pipeline tests for the materials section of the markdown export."""

    def test_all_four_section_types_render_in_single_document(self) -> None:
        """All section types (explanation, code_example, analogy, quiz) appear correctly."""
        md = build_assessment_markdown(
            session_id="sess-int-01",
            target_level="senior",
            completed_at=datetime(2026, 4, 1),
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=[_make_material("http_protocol", ALL_FOUR_SECTION_TYPES)],
        )

        # Section header and meta
        assert "## Generated Learning Materials" in md
        assert "### Http Protocol" in md
        assert "**Quality:** 85%" in md
        assert "**Bloom Score:** 80%" in md

        # Explanation
        assert "#### What is HTTP/2?" in md
        assert "HTTP/2 is a revision of the HTTP protocol." in md

        # Code example — tilde-fenced
        assert "#### HTTP/2 push example" in md
        assert "Below is a server push fragment:" in md
        assert "~~~~\nPUSH_PROMISE /styles.css\n~~~~" in md

        # Analogy (rendered as a plain section in markdown)
        assert "#### Like a highway fast lane" in md
        assert "Multiplexing lets streams share one connection." in md

        # Quiz with answer
        assert "#### Why is HTTP/2 faster?" in md
        assert "Select the correct reason." in md
        assert "> **Answer:** Header compression and stream multiplexing." in md

    def test_quality_flag_appears_alongside_quality_score_in_same_line(self) -> None:
        """quality_flag renders in the same metadata line as quality_score."""
        md = build_assessment_markdown(
            session_id="sess-int-02",
            target_level="mid",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=[
                _make_material(
                    "distributed_systems",
                    [{"type": "explanation", "title": "CAP Theorem", "body": "Body."}],
                    quality_score=0.55,
                    bloom_score=0.60,
                    quality_flag="max_iterations_reached",
                )
            ],
        )

        # Both quality score and flag must appear on the same metadata line.
        assert "**Quality:** 55%" in md
        assert "**Bloom Score:** 60%" in md
        assert "**Flag:** max_iterations_reached" in md

        # The flag string must appear on the same line as Quality.
        quality_line = next(line for line in md.splitlines() if "**Quality:**" in line)
        assert "**Flag:** max_iterations_reached" in quality_line

    def test_tilde_fencing_safely_wraps_code_containing_backtick_fences(self) -> None:
        """Code blocks that contain triple backticks are still fenced correctly with tildes."""
        injected_code = "```python\nprint('hello')\n```"
        md = build_assessment_markdown(
            session_id="sess-int-03",
            target_level="mid",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=[
                _make_material(
                    "python_basics",
                    [
                        {
                            "type": "code_example",
                            "title": "Backtick injection attempt",
                            "body": "Example:",
                            "code_block": injected_code,
                        }
                    ],
                )
            ],
        )

        # The backtick fence inside the code should be wrapped with tildes, not bare.
        assert f"~~~~\n{injected_code}\n~~~~" in md
        # The raw backtick fence must not appear outside the tilde wrapper.
        assert "```" not in md.replace(injected_code, "")

    def test_url_validation_blocks_javascript_scheme_in_resources(self) -> None:
        """javascript: URLs in resources are stripped; https: URLs render as links."""
        learning_plan = {
            "summary": "Plan",
            "total_hours": 4,
            "phases": [
                {
                    "phase_number": 1,
                    "title": "Phase 1",
                    "estimated_hours": 4,
                    "rationale": "Core skills",
                    "concepts": ["REST"],
                    "resources": [
                        {
                            "title": "Safe Resource",
                            "url": "https://developer.mozilla.org/",
                            "type": "docs",
                        },
                        {
                            "title": "Evil Link",
                            "url": "javascript:alert('xss')",
                            "type": "article",
                        },
                    ],
                }
            ],
        }
        md = build_assessment_markdown(
            session_id="sess-int-04",
            target_level="senior",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=learning_plan,
            proficiency_scores=None,
        )

        assert "[Safe Resource](https://developer.mozilla.org/)" in md
        assert "javascript:" not in md
        # Evil link renders as plain text, not a markdown link.
        assert "- Evil Link — article" in md

    def test_multiple_materials_with_mixed_validity_all_render(self) -> None:
        """Multiple materials render in order; malformed sections are skipped per-material."""
        materials = [
            _make_material(
                "concept_alpha",
                [{"type": "explanation", "title": "Alpha", "body": "Alpha body."}],
                quality_score=0.9,
            ),
            # This material has sections = "bad" — build_assessment_markdown's
            # isinstance(sections, list) guard issues a `continue` without raising.
            {
                "concept_id": "concept_broken",
                "quality_score": 0.5,
                "bloom_score": 0.5,
                "material": {"sections": "not-a-list"},
            },
            _make_material(
                "concept_beta",
                [
                    {"type": "quiz", "title": "Beta Quiz", "body": "Q?", "answer": "A."},
                ],
                quality_score=0.8,
            ),
        ]
        md = build_assessment_markdown(
            session_id="sess-int-05",
            target_level="mid",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=materials,
        )

        assert "### Concept Alpha" in md
        assert "Alpha body." in md
        assert "### Concept Beta" in md
        assert "> **Answer:** A." in md

        # concept_broken header still appears (the loop renders the header before
        # issuing `continue`), but no `####` section headings are emitted for it.
        broken_slice = md.split("### Concept Broken")[1].split("### Concept Beta")[0]
        assert "#### " not in broken_slice

    def test_quiz_section_without_answer_does_not_emit_answer_line(self) -> None:
        """A quiz section with no answer key should not emit the '> **Answer:**' line."""
        md = build_assessment_markdown(
            session_id="sess-int-06",
            target_level="mid",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=[
                _make_material(
                    "open_ended",
                    [{"type": "quiz", "title": "Open Question", "body": "Describe REST."}],
                )
            ],
        )

        assert "#### Open Question" in md
        assert "Describe REST." in md
        assert "> **Answer:**" not in md

    def test_section_with_empty_title_and_body_is_skipped(self) -> None:
        """Sections where both title and body are empty strings are not emitted."""
        md = build_assessment_markdown(
            session_id="sess-int-07",
            target_level="mid",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=[
                _make_material(
                    "ghost_concept",
                    [
                        {"type": "explanation", "title": "", "body": ""},
                        {"type": "explanation", "title": "Real Title", "body": "Real body."},
                    ],
                )
            ],
        )

        assert "#### Real Title" in md
        assert "Real body." in md
        # The empty section must not produce a bare "####" heading line.
        for line in md.splitlines():
            if line.startswith("####"):
                assert line.strip() != "####"

    def test_concept_id_underscore_to_title_case_conversion(self) -> None:
        """concept_id with underscores is converted to Title Case for the heading."""
        md = build_assessment_markdown(
            session_id="sess-int-08",
            target_level="mid",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=[
                _make_material(
                    "async_await_patterns",
                    [{"type": "explanation", "title": "T", "body": "B."}],
                )
            ],
        )

        assert "### Async Await Patterns" in md

    def test_no_materials_section_when_list_is_none(self) -> None:
        """Passing materials=None must not emit the Generated Learning Materials header."""
        md = build_assessment_markdown(
            session_id="sess-int-09",
            target_level="mid",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=None,
        )

        assert "Generated Learning Materials" not in md
        # Standard footer still present.
        assert "*Generated by OpenLearning*" in md

    def test_no_materials_section_when_list_is_empty(self) -> None:
        """Passing materials=[] must not emit the Generated Learning Materials header."""
        md = build_assessment_markdown(
            session_id="sess-int-10",
            target_level="mid",
            completed_at=None,
            knowledge_graph=None,
            gap_nodes=None,
            learning_plan=None,
            proficiency_scores=None,
            materials=[],
        )

        assert "Generated Learning Materials" not in md

    def test_full_document_structure_with_all_sections_and_materials(self) -> None:
        """Smoke test: all document sections plus materials render in the correct order."""
        knowledge_graph = {
            "nodes": [
                {
                    "concept": "REST",
                    "confidence": 0.7,
                    "bloom_level": "apply",
                    "prerequisites": [],
                    "evidence": ["Explained correctly"],
                }
            ]
        }
        gap_nodes = [
            {
                "concept": "GraphQL",
                "confidence": 0.3,
                "bloom_level": "understand",
                "prerequisites": ["REST"],
            }
        ]
        learning_plan = {
            "summary": "Master GraphQL.",
            "total_hours": 10,
            "phases": [
                {
                    "phase_number": 1,
                    "title": "Intro to GraphQL",
                    "estimated_hours": 10,
                    "rationale": "Foundation first.",
                    "concepts": ["Schemas", "Resolvers"],
                    "resources": [
                        {
                            "title": "GraphQL Docs",
                            "url": "https://graphql.org/learn/",
                            "type": "docs",
                        }
                    ],
                }
            ],
        }
        proficiency_scores = [
            {
                "skill_id": "rest",
                "skill_name": "REST",
                "score": 70,
                "confidence": 0.75,
                "bloom_level": "apply",
            }
        ]
        materials = [
            _make_material(
                "graphql_basics",
                ALL_FOUR_SECTION_TYPES,
                quality_score=0.92,
                bloom_score=0.88,
            ),
        ]

        md = build_assessment_markdown(
            session_id="sess-int-full",
            target_level="senior",
            completed_at=datetime(2026, 4, 1),
            knowledge_graph=knowledge_graph,
            gap_nodes=gap_nodes,
            learning_plan=learning_plan,
            proficiency_scores=proficiency_scores,
            materials=materials,
        )

        # Verify document section order by checking character positions.
        positions = {
            "header": md.index("# Assessment Report"),
            "proficiency": md.index("## Proficiency Scores"),
            "knowledge": md.index("## Knowledge Map"),
            "gaps": md.index("## Knowledge Gaps"),
            "plan": md.index("## Learning Plan"),
            "materials": md.index("## Generated Learning Materials"),
            "footer": md.index("*Generated by OpenLearning*"),
        }

        assert positions["header"] < positions["proficiency"]
        assert positions["proficiency"] < positions["knowledge"]
        assert positions["knowledge"] < positions["gaps"]
        assert positions["gaps"] < positions["plan"]
        assert positions["plan"] < positions["materials"]
        assert positions["materials"] < positions["footer"]

        # Spot-check cross-section content.
        assert "| REST |" in md
        assert "[GraphQL Docs](https://graphql.org/learn/)" in md
        assert "### Graphql Basics" in md
        assert "~~~~\nPUSH_PROMISE /styles.css\n~~~~" in md
        assert "> **Answer:** Header compression and stream multiplexing." in md
