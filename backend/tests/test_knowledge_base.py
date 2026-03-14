"""Tests for knowledge base loading and gap computation."""

import pytest

from app.agents.gap_analyzer import _topological_sort, analyze_gaps
from app.graph.state import BloomLevel, KnowledgeGraph, KnowledgeNode
from app.knowledge_base.loader import (
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

    def test_no_gap_when_close_to_target(self):
        target = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.7, bloom_level=BloomLevel.apply),
            ],
            edges=[],
        )
        current = KnowledgeGraph(
            nodes=[
                KnowledgeNode(concept="a", confidence=0.6, bloom_level=BloomLevel.apply),
            ],
            edges=[],
        )
        state = {"knowledge_graph": current, "target_graph": target}
        result = analyze_gaps(state)
        assert len(result["gap_nodes"]) == 0

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
