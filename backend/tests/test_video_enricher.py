"""Tests for app.agents.video_enricher — pure helpers + the async node.

ACs covered: AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-10, AC-11, AC-12, AC-13,
AC-17, AC-18, AC-19.
SRs covered: SR-02, SR-03, SR-04, SR-05, SR-08, SR-09, SR-11, SR-12, SR-13.
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


# ── _jaccard / _tokenize ────────────────────────────────────────────────


class TestPureHelpers:
    def test_jaccard_empty_query(self):
        assert ve._jaccard(set(), {"a", "b"}) == 0.0

    def test_jaccard_full_overlap(self):
        s = {"a", "b", "c"}
        assert ve._jaccard(s, s) == 1.0

    def test_jaccard_partial(self):
        score = ve._jaccard({"a", "b", "c", "d", "e"}, {"a", "b"})
        assert score == 2 / 5

    def test_tokenize_strips_stop_words_and_punctuation(self):
        toks = ve._tokenize("How to use the Postgres index?")
        assert "how" not in toks
        assert "the" not in toks
        assert "postgres" in toks
        assert "index" in toks

    def test_normalize_for_dedupe_lowercases_and_collapses_whitespace(self):
        assert ve._normalize_for_dedupe("  Postgres  Tutorial  ") == "postgres tutorial"

    def test_hash_concept_is_8_hex_chars_and_deterministic(self):
        h = ve._hash_concept("Postgres indexing")
        assert len(h) == 8
        assert all(c in "0123456789abcdef" for c in h)
        assert h == ve._hash_concept("Postgres indexing")

    def test_hash_concept_distinguishes_inputs(self):
        assert ve._hash_concept("a") != ve._hash_concept("b")


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


class TestBuildQuery:
    def test_appends_skill_domain_when_concept_name_short(self):
        q = ve._build_query("Indexing", "desc", "backend_engineering")
        assert "backend_engineering" in q

    def test_no_skill_domain_when_name_has_three_or_more_tokens(self):
        q = ve._build_query("Postgres B-tree indexing", "desc", "backend_engineering")
        assert "backend_engineering" not in q

    def test_query_has_tutorial_suffix(self):
        assert "tutorial" in ve._build_query("Indexing", "", "backend_engineering")


class TestPassesDisqualifiers:
    def _ok_pair(self):
        return _candidate("AAAAAAAAAA0"), _status("AAAAAAAAAA0")

    def test_happy_path(self):
        c, s = self._ok_pair()
        assert ve._passes_disqualifiers(c, s) is True

    def test_short_video_rejected(self):
        c, s = self._ok_pair()
        s.duration_seconds = 60  # below MIN_DURATION_SECONDS
        assert ve._passes_disqualifiers(c, s) is False

    def test_too_long_video_rejected(self):
        c, s = self._ok_pair()
        s.duration_seconds = 5 * 3_600
        assert ve._passes_disqualifiers(c, s) is False

    def test_live_broadcast_rejected(self):
        c, s = self._ok_pair()
        c.live_broadcast_content = "live"
        assert ve._passes_disqualifiers(c, s) is False

    def test_upcoming_broadcast_rejected(self):
        c, s = self._ok_pair()
        c.live_broadcast_content = "upcoming"
        assert ve._passes_disqualifiers(c, s) is False

    def test_unembeddable_rejected(self):
        c, s = self._ok_pair()
        s.embeddable = False
        assert ve._passes_disqualifiers(c, s) is False

    def test_private_rejected(self):
        c, s = self._ok_pair()
        s.privacy_status = "private"
        assert ve._passes_disqualifiers(c, s) is False

    def test_unprocessed_rejected(self):
        c, s = self._ok_pair()
        s.upload_status = "uploaded"
        assert ve._passes_disqualifiers(c, s) is False

    def test_region_blocked_rejected(self):
        c, s = self._ok_pair()
        s.region_restriction_blocked = ["DE"]
        assert ve._passes_disqualifiers(c, s) is False

    @pytest.mark.parametrize(
        "title",
        [
            "Some music tutorial",
            "Official Video",
            "song lyrics",
            "Best of the year — playlist",
        ],
    )
    def test_blocklist_titles_rejected(self, title: str):
        c, s = self._ok_pair()
        c.title = title
        assert ve._passes_disqualifiers(c, s) is False


class TestPassesRelevance:
    def test_off_topic_candidate_rejected(self):
        concept = _make_concept(name="Database indexing", description="B-tree")
        resource = _make_resource(title="Indexing guide")
        bad = _candidate("AAAAAAAAAA0", title="Top 10 SQL memes")
        bad.channel_title = "MemeTime"
        bag = ve._query_bag(concept, resource)
        passed, _ = ve._passes_relevance(bag, bad)
        assert passed is False

    def test_on_topic_candidate_accepted(self):
        concept = _make_concept(
            name="Postgres B-tree indexing",
            description="Understand B-tree and hash indexes on Postgres",
        )
        resource = _make_resource(title="Postgres B-tree indexing video")
        good = _candidate("AAAAAAAAAA0", title="Postgres B-tree indexing tutorial")
        bag = ve._query_bag(concept, resource)
        passed, score = ve._passes_relevance(bag, good)
        assert passed is True
        assert score >= ve.MIN_JACCARD_RELEVANCE


class TestSelectBest:
    def test_picks_highest_jaccard(self):
        a = _candidate("AAAAAAAAAA0")
        b = _candidate("BBBBBBBBBB0")
        s = _status("AAAAAAAAAA0")
        s2 = _status("BBBBBBBBBB0")
        pick = ve._select_best([(a, s, 0.5), (b, s2, 0.9)])
        assert pick is not None
        best, score = pick
        assert best is b
        assert score == 0.9

    def test_empty_input_returns_none(self):
        assert ve._select_best([]) is None


# ── Async node — happy path & filtering ─────────────────────────────────


def _patch_youtube(monkeypatch, *, search_returns, lookup_returns):
    """Helper to replace ys.search / ys.lookup with async fakes that record calls."""
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
    # Resource URL untouched.
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_no_video_resources_returns_empty(monkeypatch):
    """No type=video resources → {} without an API call."""
    calls = _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})
    plan = _make_plan(_make_concept(resources=[_make_resource(type_="article")]))
    assert await ve.enrich_videos({"learning_plan": plan}) == {}
    assert calls["search"] == []


@pytest.mark.asyncio
async def test_happy_path_attaches_url(monkeypatch, caplog):
    cand = _candidate("AAAAAAAAAA0", title="Postgres indexing complete tutorial walkthrough")
    cand.channel_title = "Postgres School"
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})

    concept = _make_concept(
        name="Postgres indexing",
        description="indexing",
        resources=[_make_resource(title="Postgres indexing")],
    )
    plan = _make_plan(concept)

    with caplog.at_level(logging.INFO):
        result = await ve.enrich_videos(
            {"learning_plan": plan, "skill_domain": "backend_engineering"}
        )

    assert "learning_plan" in result
    url = plan.phases[0].concepts[0].resources[0].url
    assert url == "https://www.youtube.com/watch?v=AAAAAAAAAA0"
    # SR-12: INFO log carries concept_hash + video_id + jaccard.
    attached = [r for r in caplog.records if "video_enricher.attached" in r.getMessage()]
    assert attached, caplog.text


@pytest.mark.asyncio
async def test_url_uses_validated_video_id_only(monkeypatch):
    """SR-05: URL is constructed from the 11-char video_id, never trusted from
    any string field of the candidate."""
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})

    concept = _make_concept(
        name="Postgres B-tree indexing",
        description="B-tree indexes",
        resources=[_make_resource(title="Postgres B-tree indexing")],
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

    def search_fn(query: str):
        return []

    calls = _patch_youtube(monkeypatch, search_returns=search_fn, lookup_returns={})

    concepts = [
        _make_concept(
            name=f"Concept number {i} extra",
            description=f"desc {i}",
            resources=[_make_resource(title=f"video {i}")],
        )
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

    def search_fn(query: str):
        return []

    calls = _patch_youtube(monkeypatch, search_returns=search_fn, lookup_returns={})

    # Two concepts with identical name → identical normalized query.
    c1 = _make_concept(name="Indexing", resources=[_make_resource(title="v1")])
    c2 = _make_concept(name="Indexing", resources=[_make_resource(title="v2")])
    plan = _make_plan(c1, c2)
    await ve.enrich_videos({"learning_plan": plan, "skill_domain": "backend_engineering"})

    assert len(calls["search"]) == 1


@pytest.mark.asyncio
async def test_jaccard_below_threshold_rejected(monkeypatch, caplog):
    """AC-6: relevance below 0.4 → url stays None, DEBUG no_match log."""
    cand = _candidate("AAAAAAAAAA0", title="Top 10 SQL memes")
    cand.channel_title = "MemeTime"
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})

    concept = _make_concept(
        name="Database indexing",
        description="B-tree",
        resources=[_make_resource(title="Indexing guide")],
    )
    plan = _make_plan(concept)
    with caplog.at_level(logging.DEBUG):
        await ve.enrich_videos({"learning_plan": plan})

    assert plan.phases[0].concepts[0].resources[0].url is None
    assert any("video_enricher.no_match" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_disqualifier_short_video_rejected(monkeypatch):
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0", duration=60)  # Shorts
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})

    concept = _make_concept(
        name="Postgres B-tree indexing",
        description="B-tree",
        resources=[_make_resource(title="Postgres B-tree indexing")],
    )
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_disqualifier_private_rejected(monkeypatch):
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0", privacy="private")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})
    concept = _make_concept(
        name="Postgres indexing", resources=[_make_resource(title="Postgres indexing")]
    )
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_disqualifier_region_blocked_rejected(monkeypatch):
    """AC-19: regionRestriction.blocked → reject."""
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0", blocked=["US"])
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})
    concept = _make_concept(
        name="Postgres indexing", resources=[_make_resource(title="Postgres indexing")]
    )
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_disqualifier_unembeddable_rejected(monkeypatch):
    cand = _candidate("AAAAAAAAAA0")
    stat = _status("AAAAAAAAAA0", embeddable=False)
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})
    concept = _make_concept(
        name="Postgres indexing", resources=[_make_resource(title="Postgres indexing")]
    )
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_disqualifier_live_broadcast_rejected(monkeypatch):
    cand = _candidate("AAAAAAAAAA0")
    cand.live_broadcast_content = "live"
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})
    concept = _make_concept(
        name="Postgres indexing", resources=[_make_resource(title="Postgres indexing")]
    )
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


@pytest.mark.asyncio
async def test_disqualifier_title_blocklist_rejected(monkeypatch):
    cand = _candidate("AAAAAAAAAA0", title="Postgres indexing official video")
    stat = _status("AAAAAAAAAA0")
    _patch_youtube(monkeypatch, search_returns=[cand], lookup_returns={"AAAAAAAAAA0": stat})
    concept = _make_concept(
        name="Postgres indexing", resources=[_make_resource(title="Postgres indexing")]
    )
    plan = _make_plan(concept)
    await ve.enrich_videos({"learning_plan": plan})
    assert plan.phases[0].concepts[0].resources[0].url is None


# ── Async node — error / failure paths ─────────────────────────────────


@pytest.mark.asyncio
async def test_api_error_returns_empty_dict(monkeypatch, caplog):
    """AC-3 / AC-13 / SR-07: API error → {} + WARNING log."""
    err = ys.YouTubeAPIError(403, None)
    _patch_youtube(monkeypatch, search_returns=err, lookup_returns={})
    concept = _make_concept(resources=[_make_resource()])
    plan = _make_plan(concept)
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

    # Force a tiny per-node timeout via env override.
    monkeypatch.setenv("YOUTUBE_NODE_TIMEOUT_SECONDS", "0.05")
    get_settings.cache_clear()

    concept = _make_concept(resources=[_make_resource()])
    plan = _make_plan(concept)
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

    concept = _make_concept(resources=[_make_resource()])
    plan = _make_plan(concept)
    with caplog.at_level(logging.WARNING):
        result = await ve.enrich_videos({"learning_plan": plan})

    assert result == {}
    msgs = [r.getMessage() for r in caplog.records]
    assert any("video_enricher.unexpected" in m for m in msgs)
    # Should NOT carry the raw exception text in the log message itself.
    assert not any("boom" in m for m in msgs)


@pytest.mark.asyncio
async def test_budget_circuit_breaker_skips_remaining_searches(monkeypatch, caplog):
    """SR-03: when quota_used_today() ≥ 80% of budget, no further searches."""
    monkeypatch.setenv("YOUTUBE_DAILY_QUOTA_BUDGET", "1000")
    get_settings.cache_clear()

    # 80% of 1000 = 800. We pre-spend 800 to trigger the breaker on the first call.
    ys._bump_quota(800)

    calls = _patch_youtube(monkeypatch, search_returns=[], lookup_returns={})

    concepts = [
        _make_concept(
            name=f"Concept {i} long enough",
            resources=[_make_resource(title=f"v{i}")],
        )
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


# ── No-LLM-imports check (AC-10) ────────────────────────────────────────


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


# ── Logging hygiene (SR-08) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_searches_run_concurrently_via_gather(monkeypatch):
    """Searches must fan out concurrently — semaphore caps parallelism but
    the loop is not allowed to serialize the per-concept calls (otherwise the
    30 s node timeout would fire on >3 cold-cache concepts)."""
    in_flight = 0
    peak = 0
    started = asyncio.Event()

    async def slow_search(query: str):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        if not started.is_set():
            started.set()
        # Tiny delay so multiple coroutines actually overlap.
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

    # With the previous serialized loop peak was always 1; concurrent fan-out
    # under default 5-wide semaphore must let multiple searches overlap.
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

    # 3 concepts with identical names → identical normalized queries.
    concepts = [_make_concept(name="Indexing", resources=[_make_resource()]) for _ in range(3)]
    plan = _make_plan(*concepts)
    await ve.enrich_videos({"learning_plan": plan, "skill_domain": "backend_engineering"})

    assert call_count == 1, (
        f"deduped queries issued {call_count} HTTP calls — concurrent dedupe race"
    )


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
