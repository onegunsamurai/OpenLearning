"""Tests for knowledge base loading and gap computation."""

import pytest

from app.agents.gap_analyzer import (
    PREREQ_DISCOUNT,
    _topological_sort,
    analyze_gaps,
    get_effective_confidence,
)
from app.graph.state import BloomLevel, KnowledgeGraph, KnowledgeNode, TopicStatus
from app.knowledge_base.loader import (
    build_topic_agenda,
    clear_cache,
    get_all_topics,
    get_target_graph,
    get_topics_for_level,
    load_knowledge_base,
    map_skills_to_domain,
)


@pytest.fixture(autouse=True)
def _clear_kb_cache():
    clear_cache()
    yield
    clear_cache()


class TestLoadKnowledgeBase:
    def test_loads_backend_engineering(self):
        kb = load_knowledge_base("backend_engineering")
        assert kb.domain == "backend_engineering"
        assert "junior" in kb.levels
        assert "mid" in kb.levels
        assert "senior" in kb.levels
        assert "staff" in kb.levels

    def test_raises_for_unknown_domain(self):
        with pytest.raises(FileNotFoundError):
            load_knowledge_base("nonexistent_domain")

    @pytest.mark.parametrize(
        "malicious_domain",
        [
            "../../etc/passwd",
            "../knowledge_base/backend_engineering",
            "/etc/passwd",
            ".",
            "..",
            "",
        ],
    )
    def test_rejects_path_traversal(self, malicious_domain: str):
        with pytest.raises(FileNotFoundError):
            load_knowledge_base(malicious_domain)

    def test_has_mapped_skill_ids(self):
        kb = load_knowledge_base("backend_engineering")
        assert "nodejs" in kb.mapped_skill_ids
        assert "rest-api" in kb.mapped_skill_ids


class TestGetTargetGraph:
    def test_junior_graph_has_concepts(self):
        graph = get_target_graph("backend_engineering", "junior")
        assert len(graph.nodes) > 0
        concepts = {n.concept for n in graph.nodes}
        assert "http_fundamentals" in concepts
        assert "sql_basics" in concepts

    def test_mid_includes_junior(self):
        junior = get_target_graph("backend_engineering", "junior")
        mid = get_target_graph("backend_engineering", "mid")
        junior_concepts = {n.concept for n in junior.nodes}
        mid_concepts = {n.concept for n in mid.nodes}
        assert junior_concepts.issubset(mid_concepts)
        assert len(mid_concepts) > len(junior_concepts)

    def test_senior_includes_mid(self):
        mid = get_target_graph("backend_engineering", "mid")
        senior = get_target_graph("backend_engineering", "senior")
        mid_concepts = {n.concept for n in mid.nodes}
        senior_concepts = {n.concept for n in senior.nodes}
        assert mid_concepts.issubset(senior_concepts)

    def test_graph_has_edges(self):
        graph = get_target_graph("backend_engineering", "mid")
        assert len(graph.edges) > 0
        # rest_api_basics depends on http_fundamentals
        assert ("http_fundamentals", "rest_api_basics") in graph.edges

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            get_target_graph("backend_engineering", "intern")


class TestGetTopics:
    def test_topics_for_junior(self):
        topics = get_topics_for_level("backend_engineering", "junior")
        assert "http_fundamentals" in topics
        assert len(topics) > 10

    def test_all_topics_mid(self):
        topics = get_all_topics("backend_engineering", "mid")
        assert "http_fundamentals" in topics  # from junior
        assert "api_design_patterns" in topics  # from mid
        assert len(topics) > 20


class TestMapSkillsToDomain:
    def test_maps_backend_skills(self):
        domain = map_skills_to_domain(["nodejs", "rest-api", "sql"])
        assert domain == "backend_engineering"

    def test_maps_frontend_skills(self):
        domain = map_skills_to_domain(["react", "nextjs", "css", "html-accessibility"])
        assert domain == "frontend_engineering"

    def test_maps_devops_skills(self):
        domain = map_skills_to_domain(["docker", "kubernetes", "cicd", "aws", "monitoring"])
        assert domain == "devops_engineering"

    def test_fallback_for_unknown_skills(self):
        domain = map_skills_to_domain(["totally-unknown-skill"])
        assert domain == "backend_engineering"  # fallback


class TestBuildTopicAgenda:
    def test_returns_all_concepts_up_to_level(self):
        agenda = build_topic_agenda("devops_engineering", "mid")
        concepts = [item.concept for item in agenda]
        # Should have both junior and mid concepts
        assert "linux_fundamentals" in concepts
        assert "ci_cd_pipelines" in concepts
        assert len(concepts) > 20  # 13 junior + 14 mid = 27

    def test_fundamentals_come_first(self):
        agenda = build_topic_agenda("devops_engineering", "mid")
        concepts = [item.concept for item in agenda]
        # Topics with no prerequisites should come before their dependents
        assert concepts.index("linux_fundamentals") < concepts.index("shell_scripting")
        assert concepts.index("networking_basics") < concepts.index("dns_and_http")
        assert concepts.index("container_fundamentals") < concepts.index(
            "docker_compose_orchestration"
        )

    def test_mid_concepts_after_junior_prereqs(self):
        agenda = build_topic_agenda("devops_engineering", "mid")
        concepts = [item.concept for item in agenda]
        # ci_cd_pipelines depends on version_control_workflows and container_fundamentals
        assert concepts.index("version_control_workflows") < concepts.index("ci_cd_pipelines")
        assert concepts.index("container_fundamentals") < concepts.index("ci_cd_pipelines")

    def test_all_items_start_pending(self):
        agenda = build_topic_agenda("devops_engineering", "junior")
        assert all(item.status == TopicStatus.pending for item in agenda)

    def test_items_have_correct_levels(self):
        agenda = build_topic_agenda("devops_engineering", "mid")
        levels = {item.concept: item.level for item in agenda}
        assert levels["linux_fundamentals"] == "junior"
        assert levels["ci_cd_pipelines"] == "mid"

    def test_items_have_prerequisites(self):
        agenda = build_topic_agenda("devops_engineering", "mid")
        items = {item.concept: item for item in agenda}
        assert "linux_fundamentals" in items["shell_scripting"].prerequisites

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError):
            build_topic_agenda("devops_engineering", "intern")

    def test_junior_only_excludes_mid(self):
        agenda = build_topic_agenda("devops_engineering", "junior")
        concepts = [item.concept for item in agenda]
        assert "linux_fundamentals" in concepts
        assert "ci_cd_pipelines" not in concepts


class TestGapAnalysis:
    def test_finds_gaps_below_threshold(self):
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="a", confidence=0.7, bloom_level=BloomLevel.apply, prerequisites=[]
                ),
                KnowledgeNode(
                    concept="b", confidence=0.7, bloom_level=BloomLevel.apply, prerequisites=["a"]
                ),
            ],
            edges=[("a", "b")],
        )
        current = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.3, bloom_level=BloomLevel.remember),
                # b not assessed at all
            ],
            edges=[],
        )
        state = {
            "knowledge_graph": current,
            "target_graph": target,
        }
        result = analyze_gaps(state)
        gap_concepts = [n.concept for n in result["gap_nodes"]]
        assert "a" in gap_concepts
        assert "b" in gap_concepts

    def test_small_gap_is_reported(self):
        """Skills with small but real gaps must appear in the report (issue #132)."""
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
            ],
            edges=[],
        )
        current = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.62, bloom_level=BloomLevel.apply),
            ],
            edges=[],
        )
        state = {"knowledge_graph": current, "target_graph": target}
        result = analyze_gaps(state)
        assert len(result["gap_nodes"]) == 1
        assert result["gap_nodes"][0].concept == "a"

    def test_no_gap_when_at_or_above_target(self):
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
            ],
            edges=[],
        )
        current = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
            ],
            edges=[],
        )
        state = {"knowledge_graph": current, "target_graph": target}
        result = analyze_gaps(state)
        assert len(result["gap_nodes"]) == 0

    def test_inferred_confidence_removes_gap(self):
        """When prerequisite is assessed high, dependent infers above target — no gap."""
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="a", confidence=0.4, bloom_level=BloomLevel.apply, prerequisites=[]
                ),
                KnowledgeNode(
                    concept="b",
                    confidence=0.4,
                    bloom_level=BloomLevel.apply,
                    prerequisites=["a"],
                ),
            ],
            edges=[("a", "b")],
        )
        current = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.9, bloom_level=BloomLevel.apply),
                # b not assessed — inferred: 0.9 * 0.5 = 0.45, target: 0.4
                # 0.45 > 0.4 → NOT a gap
            ],
            edges=[],
        )
        state = {"knowledge_graph": current, "target_graph": target}
        result = analyze_gaps(state)
        gap_concepts = [n.concept for n in result["gap_nodes"]]
        assert "a" not in gap_concepts  # assessed above target
        assert "b" not in gap_concepts  # inferred above target

    def test_inferred_confidence_stored_in_gap_node(self):
        """Gap node carries inferred confidence, not 0.0."""
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(
                    concept="a", confidence=0.8, bloom_level=BloomLevel.apply, prerequisites=[]
                ),
                KnowledgeNode(
                    concept="b",
                    confidence=0.8,
                    bloom_level=BloomLevel.apply,
                    prerequisites=["a"],
                ),
            ],
            edges=[("a", "b")],
        )
        current = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.5, bloom_level=BloomLevel.apply),
                # b inferred: 0.5 * 0.5 = 0.25, target: 0.8 → gap at 0.25
            ],
            edges=[],
        )
        state = {"knowledge_graph": current, "target_graph": target}
        result = analyze_gaps(state)
        gap_b = next(n for n in result["gap_nodes"] if n.concept == "b")
        assert gap_b.confidence == pytest.approx(0.25)

    def test_topological_sort_respects_prerequisites(self):
        nodes = [
            KnowledgeNode(
                concept="c", confidence=0.1, bloom_level=BloomLevel.remember, prerequisites=["b"]
            ),
            KnowledgeNode(
                concept="a", confidence=0.1, bloom_level=BloomLevel.remember, prerequisites=[]
            ),
            KnowledgeNode(
                concept="b", confidence=0.1, bloom_level=BloomLevel.remember, prerequisites=["a"]
            ),
        ]
        sorted_nodes = _topological_sort(nodes)
        concepts = [n.concept for n in sorted_nodes]
        assert concepts.index("a") < concepts.index("b")
        assert concepts.index("b") < concepts.index("c")


class TestGetEffectiveConfidence:
    """Tests for get_effective_confidence prerequisite propagation."""

    def test_returns_assessed_confidence(self):
        current = KnowledgeGraph(
            nodes=[KnowledgeNode(concept="a", confidence=0.82, bloom_level=BloomLevel.apply)]
        )
        target = KnowledgeGraph(
            nodes=[KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply)]
        )
        assert get_effective_confidence("a", current, target) == pytest.approx(0.82)

    def test_infers_from_single_prerequisite(self):
        current = KnowledgeGraph(
            nodes=[KnowledgeNode(concept="a", confidence=0.8, bloom_level=BloomLevel.apply)]
        )
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
                KnowledgeNode(
                    concept="b",
                    confidence=0.7,
                    bloom_level=BloomLevel.apply,
                    prerequisites=["a"],
                ),
            ],
            edges=[("a", "b")],
        )
        result = get_effective_confidence("b", current, target)
        assert result == pytest.approx(0.8 * PREREQ_DISCOUNT)

    def test_infers_from_multiple_prerequisites(self):
        current = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.8, bloom_level=BloomLevel.apply),
                KnowledgeNode(concept="b", confidence=0.6, bloom_level=BloomLevel.apply),
            ]
        )
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
                KnowledgeNode(concept="b", confidence=0.7, bloom_level=BloomLevel.apply),
                KnowledgeNode(
                    concept="c",
                    confidence=0.7,
                    bloom_level=BloomLevel.apply,
                    prerequisites=["a", "b"],
                ),
            ],
            edges=[("a", "c"), ("b", "c")],
        )
        expected = ((0.8 + 0.6) / 2) * PREREQ_DISCOUNT
        assert get_effective_confidence("c", current, target) == pytest.approx(expected)

    def test_returns_zero_no_prerequisites(self):
        current = KnowledgeGraph()
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
            ]
        )
        assert get_effective_confidence("a", current, target) == 0.0

    def test_returns_zero_no_assessed_prerequisites(self):
        current = KnowledgeGraph()  # nothing assessed
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
                KnowledgeNode(
                    concept="b",
                    confidence=0.7,
                    bloom_level=BloomLevel.apply,
                    prerequisites=["a"],
                ),
            ],
            edges=[("a", "b")],
        )
        assert get_effective_confidence("b", current, target) == 0.0

    def test_not_in_target_graph_returns_zero(self):
        current = KnowledgeGraph()
        target = KnowledgeGraph()
        assert get_effective_confidence("nonexistent", current, target) == 0.0

    def test_partial_prerequisites_assessed(self):
        """Only assessed prerequisites contribute to inference."""
        current = KnowledgeGraph(
            nodes=[KnowledgeNode(concept="a", confidence=0.8, bloom_level=BloomLevel.apply)]
        )
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
                KnowledgeNode(concept="b", confidence=0.7, bloom_level=BloomLevel.apply),
                KnowledgeNode(
                    concept="c",
                    confidence=0.7,
                    bloom_level=BloomLevel.apply,
                    prerequisites=["a", "b"],
                ),
            ],
        )
        # Only "a" is assessed; average of assessed = 0.8
        result = get_effective_confidence("c", current, target)
        assert result == pytest.approx(0.8 * PREREQ_DISCOUNT)
