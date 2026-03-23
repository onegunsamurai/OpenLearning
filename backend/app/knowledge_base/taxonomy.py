from __future__ import annotations

from math import ceil

from app.knowledge_base.loader import load_knowledge_base
from app.knowledge_base.schema import LEVEL_ORDER

BLOOM_INT: dict[str, int] = {
    "remember": 1,
    "understand": 2,
    "apply": 3,
    "analyze": 4,
    "evaluate": 5,
    "create": 6,
}

BLOOM_LABELS: dict[int, str] = {v: k for k, v in BLOOM_INT.items()}

BLOOM_VERBS: dict[int, list[str]] = {
    1: ["define", "list", "recall", "identify", "name", "state"],
    2: ["explain", "describe", "summarize", "paraphrase", "classify"],
    3: ["implement", "use", "demonstrate", "execute", "solve", "write"],
    4: ["compare", "differentiate", "examine", "deconstruct", "trace"],
    5: ["assess", "critique", "justify", "argue", "appraise", "defend"],
    6: ["design", "construct", "formulate", "architect", "compose"],
}

CLT_CHUNK_FACTOR: dict[str, float] = {
    "junior": 1.0,
    "mid": 1.2,
    "senior": 1.5,
    "staff": 2.0,
}

IRT_TIER_FALLBACK: dict[str, float] = {
    "junior": 0.9,
    "mid": 1.2,
    "senior": 1.5,
    "staff": 1.9,
}

_taxonomy_cache: dict[str, TaxonomyIndex] = {}


class TaxonomyIndex:
    """In-memory index over a domain's knowledge base for the content pipeline.

    Wraps KnowledgeBaseSchema with computed accessors for gap severity,
    Bloom targets, CLT parameters, and prerequisite lookups.
    """

    def __init__(self, domain: str) -> None:
        self._kb = load_knowledge_base(domain)
        self._domain = domain
        self._concepts: dict[str, dict] = {}
        self._level_map: dict[str, str] = {}

        for level_name, level_data in self._kb.levels.items():
            for concept_data in level_data.concepts:
                cid = concept_data.concept
                self._concepts[cid] = {
                    "concept": cid,
                    "target_confidence": concept_data.target_confidence,
                    "bloom_target": concept_data.bloom_target,
                    "prerequisites": concept_data.prerequisites,
                    "level": level_name,
                }
                self._level_map[cid] = level_name

    @property
    def domain(self) -> str:
        return self._domain

    def has(self, concept_id: str) -> bool:
        return concept_id in self._concepts

    def get(self, concept_id: str) -> dict:
        if concept_id not in self._concepts:
            raise KeyError(
                f"Concept '{concept_id}' not found in taxonomy for domain '{self._domain}'"
            )
        return self._concepts[concept_id]

    def bloom_target_int(self, concept_id: str) -> int:
        concept = self.get(concept_id)
        bloom_str = concept["bloom_target"]
        if bloom_str not in BLOOM_INT:
            raise ValueError(f"Unknown bloom level '{bloom_str}' for concept '{concept_id}'")
        return BLOOM_INT[bloom_str]

    def gap_severity(self, concept_id: str, current_confidence: float) -> float:
        concept = self.get(concept_id)
        target_confidence = concept["target_confidence"]
        return max(0.0, target_confidence - current_confidence)

    def irt_weight(self, concept_id: str, db_weight: float | None = None) -> float:
        if db_weight is not None:
            return db_weight
        concept = self.get(concept_id)
        tier = concept["level"]
        return IRT_TIER_FALLBACK.get(tier, 1.0)

    def prereqs(self, concept_id: str) -> list[str]:
        concept = self.get(concept_id)
        return concept["prerequisites"]

    def level(self, concept_id: str) -> str:
        concept = self.get(concept_id)
        return concept["level"]

    def clt_params(self, concept_id: str, bloom_distance: int) -> dict:
        tier = self.level(concept_id)
        chunk_factor = CLT_CHUNK_FACTOR.get(tier, 1.0)
        chunk_count = max(1, ceil(bloom_distance * chunk_factor))

        tier_idx = LEVEL_ORDER.index(tier) if tier in LEVEL_ORDER else 0
        example_count = 2 if tier_idx <= 1 else 3
        scaffolding_depth = "high" if tier_idx >= 2 else "medium"

        return {
            "chunk_count": chunk_count,
            "example_count": example_count,
            "scaffolding_depth": scaffolding_depth,
        }

    def all_concept_ids(self) -> list[str]:
        return list(self._concepts.keys())


def get_taxonomy_index(domain: str) -> TaxonomyIndex:
    """Return a cached TaxonomyIndex for the given domain."""
    if domain not in _taxonomy_cache:
        _taxonomy_cache[domain] = TaxonomyIndex(domain)
    return _taxonomy_cache[domain]


def clear_taxonomy_cache() -> None:
    """Clear taxonomy cache. Useful for tests."""
    _taxonomy_cache.clear()
