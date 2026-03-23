from __future__ import annotations

import pytest

from app.knowledge_base.taxonomy import (
    BLOOM_INT,
    IRT_TIER_FALLBACK,
    TaxonomyIndex,
    clear_taxonomy_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_taxonomy_cache()
    yield
    clear_taxonomy_cache()


@pytest.fixture
def taxonomy() -> TaxonomyIndex:
    return TaxonomyIndex("backend_engineering")


class TestBloomTargetInt:
    def test_valid_concept(self, taxonomy: TaxonomyIndex) -> None:
        # http_fundamentals has bloom_target "understand" → 2
        assert taxonomy.bloom_target_int("http_fundamentals") == BLOOM_INT["understand"]

    def test_apply_level_concept(self, taxonomy: TaxonomyIndex) -> None:
        # rest_api_basics has bloom_target "apply" → 3
        assert taxonomy.bloom_target_int("rest_api_basics") == BLOOM_INT["apply"]

    def test_missing_concept_raises(self, taxonomy: TaxonomyIndex) -> None:
        with pytest.raises(KeyError, match="not found in taxonomy"):
            taxonomy.bloom_target_int("nonexistent_concept")


class TestGapSeverity:
    def test_normal_gap(self, taxonomy: TaxonomyIndex) -> None:
        # http_fundamentals has target_confidence 0.7
        severity = taxonomy.gap_severity("http_fundamentals", 0.3)
        assert severity == pytest.approx(0.4)

    def test_zero_gap(self, taxonomy: TaxonomyIndex) -> None:
        severity = taxonomy.gap_severity("http_fundamentals", 0.7)
        assert severity == pytest.approx(0.0)

    def test_negative_clamps_to_zero(self, taxonomy: TaxonomyIndex) -> None:
        severity = taxonomy.gap_severity("http_fundamentals", 0.9)
        assert severity == 0.0

    def test_full_gap(self, taxonomy: TaxonomyIndex) -> None:
        severity = taxonomy.gap_severity("http_fundamentals", 0.0)
        assert severity == pytest.approx(0.7)


class TestIrtWeight:
    def test_with_db_weight(self, taxonomy: TaxonomyIndex) -> None:
        weight = taxonomy.irt_weight("http_fundamentals", db_weight=2.5)
        assert weight == 2.5

    def test_fallback_junior_tier(self, taxonomy: TaxonomyIndex) -> None:
        # http_fundamentals is junior level
        weight = taxonomy.irt_weight("http_fundamentals")
        assert weight == IRT_TIER_FALLBACK["junior"]

    def test_missing_concept_raises(self, taxonomy: TaxonomyIndex) -> None:
        with pytest.raises(KeyError, match="not found in taxonomy"):
            taxonomy.irt_weight("nonexistent_concept")


class TestPrereqs:
    def test_with_dependencies(self, taxonomy: TaxonomyIndex) -> None:
        prereqs = taxonomy.prereqs("rest_api_basics")
        assert "http_fundamentals" in prereqs

    def test_no_dependencies(self, taxonomy: TaxonomyIndex) -> None:
        prereqs = taxonomy.prereqs("http_fundamentals")
        assert prereqs == []


class TestCltParams:
    def test_junior_tier(self, taxonomy: TaxonomyIndex) -> None:
        params = taxonomy.clt_params("http_fundamentals", bloom_distance=2)
        assert params["chunk_count"] == 2  # ceil(2 * 1.0)
        assert params["example_count"] == 2
        assert params["scaffolding_depth"] == "medium"

    def test_bloom_distance_one(self, taxonomy: TaxonomyIndex) -> None:
        params = taxonomy.clt_params("http_fundamentals", bloom_distance=1)
        assert params["chunk_count"] == 1  # ceil(1 * 1.0)

    def test_minimum_chunk_count(self, taxonomy: TaxonomyIndex) -> None:
        params = taxonomy.clt_params("http_fundamentals", bloom_distance=0)
        assert params["chunk_count"] >= 1


class TestTopologicalSort:
    def test_linear_chain(self, taxonomy: TaxonomyIndex) -> None:
        from app.agents.content_nodes import _topological_sort

        # http_fundamentals → rest_api_basics → crud_operations
        concept_ids = ["crud_operations", "rest_api_basics", "http_fundamentals"]
        sorted_ids = _topological_sort(concept_ids, taxonomy)

        # http_fundamentals should come before rest_api_basics, which should come before crud_operations
        assert sorted_ids.index("http_fundamentals") < sorted_ids.index("rest_api_basics")
        assert sorted_ids.index("rest_api_basics") < sorted_ids.index("crud_operations")

    def test_no_deps(self, taxonomy: TaxonomyIndex) -> None:
        from app.agents.content_nodes import _topological_sort

        concept_ids = ["http_fundamentals", "error_handling"]
        sorted_ids = _topological_sort(concept_ids, taxonomy)
        assert set(sorted_ids) == {"http_fundamentals", "error_handling"}

    def test_diamond_dependency(self, taxonomy: TaxonomyIndex) -> None:
        from app.agents.content_nodes import _topological_sort

        # sql_basics → database_schema_design, sql_basics → orm_basics
        concept_ids = ["database_schema_design", "orm_basics", "sql_basics"]
        sorted_ids = _topological_sort(concept_ids, taxonomy)
        assert sorted_ids.index("sql_basics") < sorted_ids.index("database_schema_design")
        assert sorted_ids.index("sql_basics") < sorted_ids.index("orm_basics")


class TestTaxonomyIndexMisc:
    def test_has_concept(self, taxonomy: TaxonomyIndex) -> None:
        assert taxonomy.has("http_fundamentals") is True
        assert taxonomy.has("nonexistent") is False

    def test_domain_property(self, taxonomy: TaxonomyIndex) -> None:
        assert taxonomy.domain == "backend_engineering"

    def test_all_concept_ids_not_empty(self, taxonomy: TaxonomyIndex) -> None:
        all_ids = taxonomy.all_concept_ids()
        assert len(all_ids) > 0
        assert "http_fundamentals" in all_ids

    def test_level(self, taxonomy: TaxonomyIndex) -> None:
        assert taxonomy.level("http_fundamentals") == "junior"
