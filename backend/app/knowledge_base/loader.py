from __future__ import annotations

from pathlib import Path

import yaml

from app.graph.state import BloomLevel, KnowledgeGraph, KnowledgeNode

_KB_DIR = Path(__file__).parent
_cache: dict[str, dict] = {}


def load_knowledge_base(domain: str) -> dict:
    if domain in _cache:
        return _cache[domain]
    path = _KB_DIR / f"{domain}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Knowledge base not found: {domain}")
    with open(path) as f:
        data = yaml.safe_load(f)
    _cache[domain] = data
    return data


def get_target_graph(domain: str, level: str) -> KnowledgeGraph:
    """Build a KnowledgeGraph containing all concepts up to and including the target level."""
    kb = load_knowledge_base(domain)
    level_order = ["junior", "mid", "senior", "staff"]
    if level not in level_order:
        raise ValueError(f"Unknown level: {level}. Must be one of {level_order}")

    target_idx = level_order.index(level)
    nodes: list[KnowledgeNode] = []
    edges: list[tuple[str, str]] = []
    seen_concepts: set[str] = set()

    for lvl in level_order[: target_idx + 1]:
        level_data = kb.get("levels", {}).get(lvl, {})
        for concept_data in level_data.get("concepts", []):
            concept = concept_data["concept"]
            if concept in seen_concepts:
                continue
            seen_concepts.add(concept)
            nodes.append(
                KnowledgeNode(
                    concept=concept,
                    confidence=concept_data["target_confidence"],
                    bloom_level=BloomLevel(concept_data["bloom_target"]),
                    prerequisites=concept_data.get("prerequisites", []),
                    evidence=[],
                )
            )
            for prereq in concept_data.get("prerequisites", []):
                edges.append((prereq, concept))

    return KnowledgeGraph(nodes=nodes, edges=edges)


def get_topics_for_level(domain: str, level: str) -> list[str]:
    """Get the topic names for a specific level."""
    kb = load_knowledge_base(domain)
    level_data = kb.get("levels", {}).get(level, {})
    return [c["concept"] for c in level_data.get("concepts", [])]


def get_all_topics(domain: str, up_to_level: str) -> list[str]:
    """Get all topic names up to and including the given level."""
    graph = get_target_graph(domain, up_to_level)
    return [node.concept for node in graph.nodes]


def map_skills_to_domain(skill_ids: list[str]) -> str:
    """Map selected skill IDs to the best-matching knowledge base domain.

    Counts overlap between selected skills and each domain's mapped_skill_ids.
    Returns the domain with the most overlap. Falls back to 'backend_engineering'.
    """
    best_domain = "backend_engineering"
    best_count = 0

    for yaml_file in _KB_DIR.glob("*.yaml"):
        domain = yaml_file.stem
        try:
            kb = load_knowledge_base(domain)
        except Exception:
            continue
        mapped = set(kb.get("mapped_skill_ids", []))
        overlap = len(mapped & set(skill_ids))
        if overlap > best_count:
            best_count = overlap
            best_domain = domain
    return best_domain
