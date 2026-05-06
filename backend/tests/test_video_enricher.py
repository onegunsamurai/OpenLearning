"""Tests for app.agents.video_enricher — pure helpers + the async node.

ACs (post-gate-simplification): AC-2 (feature flag), AC-3 (graceful error),
AC-7 (cap), AC-10 (no LLM), AC-11 (cap pre-call), AC-12 (dedupe), AC-13.
SRs covered: SR-02 (PII), SR-03 (cap+budget), SR-04 (timeouts), SR-05 (URL
from validated video_id), SR-08 (concept hash in logs), SR-12 (audit log).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

from app.agents import video_enricher as ve
from app.config import get_settings
from app.graph.state import ConceptItem, LearningPhase, LearningPlan, Resource
from app.services import youtube as ys

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Each test starts with a clean cache and a known API key."""
    monkeypatch.setenv("YOUTUBE_API_KEY", "AIza-test-key")
    get_settings.cache_clear()
    ys.clear_caches()
    yield
    ys.clear_caches()
    get_settings.cache_clear()


def _make_resource(title: str = "Some video resource", type_: str = "video") -> Resource:
    return Resource(type=type_, title=title, url=None)


def _make_concept(
    name: str = "Postgres indexing",
    description: str = "B-tree and hash indexes on Postgres",
    resources: list[Resource] | None = None,
) -> ConceptItem:
    return ConceptItem(
        key="c1",
        name=name,
        description=description,
        resources=resources if resources is not None else [_make_resource()],
    )


def _make_plan(*concepts: ConceptItem) -> LearningPlan:
    return LearningPlan(
        phases=[
            LearningPhase(
                phase_number=1,
                title="Phase 1",
                concepts=list(concepts),
                rationale="test",
                estimated_hours=1.0,
            )
        ],
        total_hours=1.0,
        summary="test plan",
    )


def _candidate(video_id: str, title: str = "Postgres indexing tutorial") -> ys.VideoCandidate:
    return ys.VideoCandidate(
        video_id=video_id,
        title=title,
        channel_title="School of Postgres",
        live_broadcast_content="none",
    )


def _status(
    video_id: str,
    *,
    duration: int = 600,
    privacy: str = "public",
    embeddable: bool = True,
    upload: str = "processed",
    blocked: list[str] | None = None,
) -> ys.VideoStatus:
    return ys.VideoStatus(
        video_id=video_id,
        duration_seconds=duration,
        upload_status=upload,
        privacy_status=privacy,
        embeddable=embeddable,
        region_restriction_blocked=blocked or [],
    )


# ── _hash_concept ───────────────────────────────────────────────────────


class TestHashConcept:
    def test_returns_8_hex_chars_and_is_deterministic(self):
        h = ve._hash_concept("Postgres indexing")
        assert len(h) == 8
        assert all(c in "0123456789abcdef" for c in h)
        assert h == ve._hash_concept("Postgres indexing")

    def test_distinguishes_inputs(self):
        assert ve._hash_concept("a") != ve._hash_concept("b")


# ── _sanitize_query ─────────────────────────────────────────────────────


class TestSanitizeQuery:
    def test_strips_email(self):
        cleaned = ve._sanitize_query("postgres me@example.com indexing")
        assert "me@example.com" not in cleaned
        assert "@" not in cleaned

    def test_strips_phone(self):
        assert "+1 555-123-4567" not in ve._sanitize_query("call +1 555-123-4567 now")

    def test_strips_company_suffix(self):
        cleaned = ve._sanitize_query("Postgres at Acme Corp")
        assert "Acme Corp" not in cleaned

    def test_strips_search_operators(self):
        cleaned = ve._sanitize_query('site:foo.com intitle:bar "exact"')
        assert "site:" not in cleaned
        assert "intitle:" not in cleaned
        assert '"' not in cleaned

    def test_strips_control_chars(self):
        cleaned = ve._sanitize_query("postgres\x00indexing")
        assert "\x00" not in cleaned

    def test_truncates_to_max_length(self):
        cleaned = ve._sanitize_query("x" * 300)
        assert len(cleaned) == ve.QUERY_MAX_LENGTH

    def test_collapses_whitespace(self):
        assert ve._sanitize_query("a    b    c") == "a b c"


# ── _build_query ────────────────────────────────────────────────────────


class TestBuildQuery:
    def test_appends_skill_domain_when_concept_name_short(self):
        q = ve._build_query("Indexing", "desc", "backend_engineering")
        assert "backend_engineering" in q

    def test_no_skill_domain_when_name_has_three_or_more_tokens(self):
        q = ve._build_query("Postgres B-tree indexing", "desc", "backend_engineering")
        assert "backend_engineering" not in q

    def test_query_has_tutorial_suffix(self):
        assert "tutorial" in ve._build_query("Indexing", "", "backend_engineering")


# ── _normalize_for_dedupe ───────────────────────────────────────────────


class TestNormalize:
    def test_lowercases_and_collapses_whitespace(self):
        assert ve._normalize_for_dedupe("  Postgres  Tutorial  ") == "postgres tutorial"


# ── _passes_filter ──────────────────────────────────────────────────────


class TestPassesFilter:
    def _ok_pair(self):
        return _candidate("AAAAAAAAAA0"), _status("AAAAAAAAAA0")

    def test_happy_path(self):
        c, s = self._ok_pair()
        assert ve._passes_filter(c, s) is True

    def test_short_video_rejected(self):
        c, s = self._ok_pair()
        s.duration_seconds = 60  # below MIN_DURATION_SECONDS
        assert ve._passes_filter(c, s) is False

    def test_live_broadcast_rejected(self):
        c, s = self._ok_pair()
        c.live_broadcast_content = "live"
        assert ve._passes_filter(c, s) is False

    def test_upcoming_broadcast_rejected(self):
        c, s = self._ok_pair()
        c.live_broadcast_content = "upcoming"
        assert ve._passes_filter(c, s) is False

    @pytest.mark.parametrize(
        "title",
        [
            "Some music video",
            "Official Video — Release",
            "song lyrics",
            "Track — Official Audio",
        ],
    )
    def test_blocklist_titles_rejected(self, title: str):
        c, s = self._ok_pair()
        c.title = title
        assert ve._passes_filter(c, s) is False

    def test_playlist_NOT_rejected(self):
        """'playlist' is intentionally not in the blocklist — legit tutorials
        often live on playlists."""
        c, s = self._ok_pair()
        c.title = "Kubernetes tutorial — full playlist"
        assert ve._passes_filter(c, s) is True

    def test_offtopic_title_NOT_filtered(self):
        """The simple gate trusts YouTube's relevance ranking; it does NOT
        do its own topic check (the previous Jaccard gate did, and rejected
        everything in practice)."""
        c, s = self._ok_pair()
        c.title = "Top 10 SQL memes"
        assert ve._passes_filter(c, s) is True


# ── Async node ──────────────────────────────────────────────────────────


def _patch_youtube(monkeypatch, *, search_returns, lookup_returns):
    """Replace ys.search / ys.lookup with async fakes that record calls."""
    calls = {"search": [], "lookup": []}

    async def fake_search(query: str):
        calls["search"].append(query)
        if isinstance(search_returns, Exception):
            raise search_returns
        if callable(search_returns):
            return search_returns(query)
        return search_returns

    async def fake_lookup(ids):
        calls["lookup"].append(list(ids))
        if isinstance(lookup_returns, Exception):
            raise lookup_returns
        if callable(lookup_returns):
            return lookup_returns(ids)
        return lookup_returns

    monkeypatch.setattr(ys, "search", fake_search)
    monkeypatch.setattr(ys, "lookup", fake_lookup)
    return calls


@pytest.mark.asyncio
async def test_empty_key_short_circuits(monkeypatch):
    """AC-2: missing YOUTUBE_API_KEY → no API calls, no mutation, return {}."""
    monkeypatch.setenv("YOUTUBE_API_KEY", "")
    get_settings.cache_clear()

    calls = _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})
    plan = _make_plan(_make_concept())
    result = await ve.enrich_videos({"learning_plan": plan})

    assert result == {}
    assert calls["search"] == []
    assert calls["lookup"] == []
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_no_video_resources_returns_empty(monkeypatch):
    calls = _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})
    plan = _make_plan(_make_concept(resources=[_make_resource(type_="article")]))
    assert await ve.enrich_videos({"learning_plan": plan}) == {}
    assert calls["search"] == []


@pytest.mark.asyncio
async def test_happy_path_attaches_first_candidate(monkeypatch, caplog):
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})

    concept = _make_concept(
        name="Postgres indexing", resources=[_make_resource(title="Postgres indexing")]
    )
    plan = _make_plan(concept)

    with caplog.at_level(logging.INFO):
        result = await ve.enrich_videos({"learning_plan": plan})

    assert "learning_plan" in result
    assert (
        plan.phases[0].concepts[0].resources[0].url == "https://www.youtube.com/watch?v=AAAAAAAAAA0"
    )
    assert any("video_enricher.attached" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_first_candidate_failing_filter_falls_back_to_next(monkeypatch):
    """If candidate #1 is a Short, candidate #2 should be picked instead."""
    short = _candidate("SHORT000000", title="Postgres tutorial")
    long_ = _candidate("LONG0000000", title="Postgres tutorial")
    _patch_youtube(
        monkeypatch,
        search_returns=[short, long_],
        lookup_returns={
            "SHORT000000": _status("SHORT000000", duration=45),  # Short
            "LONG0000000": _status("LONG0000000", duration=600),
        },
    )
    concept = _make_concept(name="Postgres indexing", resources=[_make_resource()])
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})
    assert (
        plan.phases[0].concepts[0].resources[0].url == "https://www.youtube.com/watch?v=LONG0000000"
    )


@pytest.mark.asyncio
async def test_url_uses_validated_video_id_only(monkeypatch):
    """SR-05: URL is constructed from the 11-char video_id, never trusted from
    any string field of the candidate."""
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})

    concept = _make_concept(
        name="Postgres indexing", resources=[_make_resource(title="Postgres indexing")]
    )
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})

    url = plan.phases[0].concepts[0].resources[0].url
    assert url == "https://www.youtube.com/watch?v=AAAAAAAAAA0"


@pytest.mark.asyncio
async def test_cap_enforced_pre_call(monkeypatch, caplog):
    """AC-11 / SR-03: searches stop once the per-plan cap is hit."""
    monkeypatch.setenv("MAX_VIDEO_LOOKUPS_PER_PLAN", "3")
    get_settings.cache_clear()

    calls = _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})

    concepts = [
        _make_concept(name=f"Concept number {i} extra", resources=[_make_resource(title=f"v{i}")])
        for i in range(10)
    ]
    plan = _make_plan(*concepts)

    with caplog.at_level(logging.INFO):
        await ve.enrich_videos({"learning_plan": plan})

    assert len(calls["search"]) == 3
    assert any("video_enricher.cap_reached" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_dedupe_within_plan(monkeypatch):
    """AC-12: identical normalized queries result in exactly one search call."""
    calls = _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})

    c1 = _make_concept(name="Indexing", resources=[_make_resource(title="v1")])
    c2 = _make_concept(name="Indexing", resources=[_make_resource(title="v2")])
    plan = _make_plan(c1, c2)
    await ve.enrich_videos({"learning_plan": plan, "skill_domain": "backend_engineering"})

    assert len(calls["search"]) == 1


@pytest.mark.asyncio
async def test_no_results_leaves_url_none(monkeypatch, caplog):
    _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})
    plan = _make_plan(_make_concept(resources=[_make_resource()]))
    with caplog.at_level(logging.DEBUG):
        await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_short_video_rejected_by_node(monkeypatch):
    """Integration: a single short video result yields no URL."""
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0", duration=45)  # Short
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})
    plan = _make_plan(_make_concept(resources=[_make_resource()]))
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_live_broadcast_rejected_by_node(monkeypatch):
    cand = _candidate("AAAAAAAAAA0")
    cand.live_broadcast_content = "live"
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})
    plan = _make_plan(_make_concept(resources=[_make_resource()]))
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_blocklist_title_rejected_by_node(monkeypatch):
    cand = _candidate("AAAAAAAAAA0", title="Postgres indexing official video")
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})
    plan = _make_plan(_make_concept(resources=[_make_resource()]))
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_api_error_returns_empty_dict(monkeypatch, caplog):
    """AC-3 / AC-13 / SR-07: API error → {} + WARNING log."""
    err = ys.YouTubeAPIError(403, None)
    _patch_youtube(monkeypatch, search_returns=err, lookup_returns={})
    plan = _make_plan(_make_concept(resources=[_make_resource()]))
    with caplog.at_level(logging.WARNING):
        result = await ve.enrich_videos({"learning_plan": plan})
    assert result == {}
    assert plan.phases[0].concepts[0].resources[0].url is None
    assert any("video_enricher.api_error" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_node_timeout_returns_empty_dict(monkeypatch, caplog):
    """SR-04: when the body exceeds NODE_TIMEOUT, fall back to {}."""

    async def slow_search(query: str):
        await asyncio.sleep(5)
        return []

    monkeypatch.setattr(ys, "search", slow_search)

    async def fake_lookup(ids):
        return {}

    monkeypatch.setattr(ys, "lookup", fake_lookup)

    monkeypatch.setenv("YOUTUBE_NODE_TIMEOUT_SECONDS", "0.05")
    get_settings.cache_clear()

    plan = _make_plan(_make_concept(resources=[_make_resource()]))
    with caplog.at_level(logging.WARNING):
        result = await ve.enrich_videos({"learning_plan": plan})

    assert result == {}
    assert any("video_enricher.timeout" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_unexpected_exception_swallowed(monkeypatch, caplog):
    """AC-13: any RuntimeError inside the body → {} + WARNING log, no exc text."""

    async def broken_search(query):
        raise RuntimeError("boom")

    monkeypatch.setattr(ys, "search", broken_search)

    async def fake_lookup(ids):
        return {}

    monkeypatch.setattr(ys, "lookup", fake_lookup)

    plan = _make_plan(_make_concept(resources=[_make_resource()]))
    with caplog.at_level(logging.WARNING):
        result = await ve.enrich_videos({"learning_plan": plan})

    assert result == {}
    msgs = [r.getMessage() for r in caplog.records]
    assert any("video_enricher.unexpected" in m for m in msgs)
    assert not any("boom" in m for m in msgs)


@pytest.mark.asyncio
async def test_budget_circuit_breaker_skips_remaining_searches(monkeypatch, caplog):
    """SR-03: when quota_used_today() ≥ 80% of budget, no further searches."""
    monkeypatch.setenv("YOUTUBE_DAILY_QUOTA_BUDGET", "1000")
    get_settings.cache_clear()
    ys._bump_quota(800)  # 80% of 1000 → trip the breaker

    calls = _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})

    concepts = [
        _make_concept(name=f"Concept {i} long enough", resources=[_make_resource(title=f"v{i}")])
        for i in range(5)
    ]
    plan = _make_plan(*concepts)

    with caplog.at_level(logging.WARNING):
        await ve.enrich_videos({"learning_plan": plan})

    assert calls["search"] == []
    assert any("video_enricher.budget_reached" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_pii_stripped_from_outbound_query(monkeypatch):
    """SR-02: emails/phones/company-suffix do not reach YouTube."""
    calls = _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})

    concept = _make_concept(
        name="Postgres at Acme Corp",
        description="Reach me at me@example.com or +1 555-123-4567",
        resources=[_make_resource()],
    )
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})

    sent = calls["search"][0]
    assert "Acme Corp" not in sent
    assert "me@example.com" not in sent
    assert "555-123-4567" not in sent


@pytest.mark.parametrize(
    "path",
    [
        "app/agents/video_enricher.py",
        "app/services/youtube.py",
    ],
)
def test_module_contains_no_llm_imports(path: str):
    """AC-10: video discovery / validation must not depend on any LLM SDK."""
    src = (Path(__file__).parent.parent / path).read_text(encoding="utf-8")
    for forbidden in (
        "import langchain",
        "from langchain",
        "import anthropic",
        "from anthropic",
        "import openai",
        "from openai",
    ):
        assert forbidden not in src, f"{path} contains forbidden import: {forbidden}"


@pytest.mark.asyncio
async def test_searches_run_concurrently_via_gather(monkeypatch):
    """Searches must fan out concurrently — semaphore caps parallelism but
    the loop must not serialize the per-concept calls."""
    in_flight = 0
    peak = 0

    async def slow_search(query: str):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return []

    monkeypatch.setattr(ys, "search", slow_search)

    async def fake_lookup(ids):
        return {}

    monkeypatch.setattr(ys, "lookup", fake_lookup)

    concepts = [
        _make_concept(name=f"Concept number {i} extra", resources=[_make_resource()])
        for i in range(5)
    ]
    plan = _make_plan(*concepts)
    await ve.enrich_videos({"learning_plan": plan})

    assert peak >= 2, f"searches were serialized (peak in-flight = {peak})"


@pytest.mark.asyncio
async def test_concurrent_dedupe_does_not_double_spend(monkeypatch):
    """AC-12 holds under concurrent fan-out: two coroutines for the same
    normalized query must not both miss the cache and issue duplicate HTTP."""
    call_count = 0

    async def counting_search(query: str):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.01)
        return []

    monkeypatch.setattr(ys, "search", counting_search)

    async def fake_lookup(ids):
        return {}

    monkeypatch.setattr(ys, "lookup", fake_lookup)

    concepts = [_make_concept(name="Indexing", resources=[_make_resource()]) for _ in range(3)]
    plan = _make_plan(*concepts)
    await ve.enrich_videos({"learning_plan": plan, "skill_domain": "backend_engineering"})

    assert call_count == 1


@pytest.mark.asyncio
async def test_logs_use_concept_hash_not_raw_text(monkeypatch, caplog):
    """SR-08: INFO log lines must reference concepts by 8-hex hash only."""
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})

    secret_concept_name = "TopSecretInternalProjectName Postgres indexing"
    concept = _make_concept(
        name=secret_concept_name,
        description="Postgres B-tree indexing description",
        resources=[_make_resource(title="Postgres indexing")],
    )
    plan = _make_plan(concept)
    with caplog.at_level(logging.INFO):
        await ve.enrich_videos({"learning_plan": plan})

    for record in caplog.records:
        assert "TopSecretInternalProjectName" not in record.getMessage()
