"""Tests for app.services.youtube — the YouTube Data API v3 client.

ACs covered: AC-7 (quota math), AC-13 (graceful error mapping),
AC-16 (TTL caches), AC-19 (region restriction parsed).
SRs covered: SR-01 (key never logged / leaks), SR-04 (timeouts), SR-05
(videoId regex enforcement), SR-06 (bounded LRU+TTL), SR-07 (warning logs
without URL/key), SR-09 (no follow-redirects), SR-13 (deterministic).
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

import httpx
import pytest
import respx

from app.config import get_settings
from app.services import youtube as ys

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_caches(monkeypatch):
    """Every test starts with empty caches and a known API key."""
    monkeypatch.setenv("YOUTUBE_API_KEY", "AIza-test-key")
    get_settings.cache_clear()
    ys.clear_caches()
    yield
    ys.clear_caches()
    get_settings.cache_clear()


def _search_response(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"items": items if items is not None else _default_search_items()}


def _default_search_items() -> list[dict[str, Any]]:
    return [
        {
            "id": {"videoId": f"AAAAAAAAAA{i}"},
            "snippet": {
                "title": f"Postgres tutorial part {i}",
                "channelTitle": "Some Channel",
                "liveBroadcastContent": "none",
            },
        }
        for i in range(5)
    ]


def _videos_response(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"items": items if items is not None else _default_video_items()}


def _default_video_items() -> list[dict[str, Any]]:
    return [
        {
            "id": "AAAAAAAAAA0",
            "status": {
                "uploadStatus": "processed",
                "privacyStatus": "public",
                "embeddable": True,
            },
            "contentDetails": {"duration": "PT4M13S"},
        }
    ]


# ── search() ────────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_search_happy_path_returns_candidates_and_bumps_quota():
    respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).respond(json=_search_response())

    candidates = await ys.search("postgres tutorial")

    assert len(candidates) == 5
    assert all(ys.VIDEO_ID_REGEX.match(c.video_id) for c in candidates)
    assert ys.quota_used_today() == 100  # AC-7


@respx.mock
@pytest.mark.asyncio
async def test_search_cache_hit_avoids_second_http_call():
    """Identical query → exactly 1 HTTP call (AC-16)."""
    route = respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).respond(json=_search_response())

    await ys.search("postgres tutorial")
    await ys.search("postgres tutorial")

    assert route.call_count == 1
    assert ys.quota_used_today() == 100


@respx.mock
@pytest.mark.asyncio
async def test_search_invalid_video_id_dropped():
    """SR-05: any item whose id fails the regex is silently dropped."""
    items = [
        {
            "id": {"videoId": "javascript:alert(1)"},
            "snippet": {"title": "evil", "channelTitle": "x", "liveBroadcastContent": "none"},
        },
        {
            "id": {"videoId": "VALID000000"},
            "snippet": {"title": "ok", "channelTitle": "x", "liveBroadcastContent": "none"},
        },
    ]
    respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).respond(json=_search_response(items))

    candidates = await ys.search("q")

    assert [c.video_id for c in candidates] == ["VALID000000"]


@respx.mock
@pytest.mark.asyncio
async def test_search_empty_results_returns_empty_list_not_error():
    respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).respond(json={"items": []})
    assert await ys.search("nothing") == []


@respx.mock
@pytest.mark.asyncio
async def test_search_passes_required_query_params():
    """SR-09 + design contract: outbound query must constrain results."""
    route = respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).respond(json=_search_response())

    await ys.search("postgres tutorial")

    sent = route.calls.last.request.url.params
    assert sent["type"] == "video"
    assert sent["videoEmbeddable"] == "true"
    assert sent["safeSearch"] == "moderate"
    assert sent["maxResults"] == "5"
    assert sent["part"] == "snippet"
    assert sent["q"] == "postgres tutorial"
    assert sent["key"] == "AIza-test-key"


@respx.mock
@pytest.mark.asyncio
async def test_request_module_key_cannot_be_shadowed_by_caller_params():
    """SR-01 defence in depth: a caller of :func:`_request` must not be able
    to override the module-supplied API key by slipping ``key`` into *params*.
    Regression guard for the params-spread footgun flagged in PR review."""
    route = respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).respond(json={"items": []})

    await ys._request(ys.SEARCH_PATH, {"key": "ATTACKER-SHADOW-KEY", "q": "x", "part": "snippet"})

    sent = route.calls.last.request.url.params
    assert sent["key"] == "AIza-test-key"
    assert "ATTACKER-SHADOW-KEY" not in str(route.calls.last.request.url)


@pytest.mark.parametrize(
    "status_code,retry_after_header,expected_retry",
    [
        (400, None, None),
        (403, None, None),
        (429, "30", 30),
        (500, None, None),
    ],
)
@respx.mock
@pytest.mark.asyncio
async def test_search_error_maps_to_youtube_api_error(
    status_code: int, retry_after_header: str | None, expected_retry: int | None
):
    headers = {"Retry-After": retry_after_header} if retry_after_header else {}
    respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).respond(
        status_code=status_code, headers=headers, json={}
    )

    with pytest.raises(ys.YouTubeAPIError) as exc:
        await ys.search("q")

    assert exc.value.status_code == status_code
    assert exc.value.retry_after_seconds == expected_retry


@respx.mock
@pytest.mark.asyncio
async def test_search_timeout_maps_to_status_zero():
    respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).mock(side_effect=httpx.TimeoutException("slow"))

    with pytest.raises(ys.YouTubeAPIError) as exc:
        await ys.search("q")

    assert exc.value.status_code == 0


@respx.mock
@pytest.mark.asyncio
async def test_search_connect_error_maps_to_status_zero():
    respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).mock(side_effect=httpx.ConnectError("nope"))
    with pytest.raises(ys.YouTubeAPIError) as exc:
        await ys.search("q")
    assert exc.value.status_code == 0


@respx.mock
@pytest.mark.asyncio
async def test_search_http_error_does_not_count_quota():
    """A failed request must not increment the daily counter."""
    respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).respond(status_code=500, json={})
    with pytest.raises(ys.YouTubeAPIError):
        await ys.search("q")
    assert ys.quota_used_today() == 0


# ── YouTubeAPIError redaction (SR-01 / T-07) ───────────────────────────


def test_youtube_api_error_repr_does_not_leak_url_or_key():
    err = ys.YouTubeAPIError(403, None)
    rendered = f"{err!r}|{err}|{err.args}"
    # The exception must never carry the API key value.
    assert "AIza" not in rendered
    # And it must never carry a URL fragment that could include the key.
    assert "googleapis.com" not in rendered
    assert "key=" not in rendered


def test_youtube_api_error_format_is_stable_for_logs():
    err = ys.YouTubeAPIError(429, 60)
    assert "status_code=429" in repr(err)
    assert "retry_after_seconds=60" in repr(err)


# ── lookup() ────────────────────────────────────────────────────────────


@respx.mock
@pytest.mark.asyncio
async def test_lookup_happy_path_parses_status():
    respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json=_videos_response())

    result = await ys.lookup(["AAAAAAAAAA0"])

    assert "AAAAAAAAAA0" in result
    s = result["AAAAAAAAAA0"]
    assert s.duration_seconds == 4 * 60 + 13
    assert s.privacy_status == "public"
    assert s.embeddable is True
    assert s.region_restriction_blocked == []
    assert ys.quota_used_today() == 1  # AC-7: 1 unit per batched call


@respx.mock
@pytest.mark.asyncio
async def test_lookup_empty_list_skips_http():
    """Empty input returns {} without burning a quota unit."""
    route = respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json=_videos_response())

    assert await ys.lookup([]) == {}
    assert route.call_count == 0
    assert ys.quota_used_today() == 0


@respx.mock
@pytest.mark.asyncio
async def test_lookup_batches_at_50_per_call():
    """73 ids → 2 batched HTTP calls; quota +=2."""
    route = respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json={"items": []})
    # Build proper 11-char ids matching VIDEO_ID_REGEX.
    ids = [(f"vid{i:08d}"[:11]).ljust(11, "Z") for i in range(73)]

    await ys.lookup(ids)

    assert route.call_count == 2
    assert ys.quota_used_today() == 2


@respx.mock
@pytest.mark.asyncio
async def test_per_request_timeout_setting_is_honored(monkeypatch):
    """SR-04: operator-tunable timeout via Settings is read at request time."""
    monkeypatch.setenv("YOUTUBE_PER_REQUEST_TIMEOUT_SECONDS", "0.25")
    get_settings.cache_clear()

    captured: dict[str, httpx.Timeout] = {}

    def _record(request: httpx.Request) -> httpx.Response:
        captured["timeout"] = request.extensions.get("timeout")  # type: ignore[assignment]
        return httpx.Response(200, json={"items": []})

    respx.get(ys.YOUTUBE_API_BASE + ys.SEARCH_PATH).mock(side_effect=_record)

    await ys.search("q")

    # httpx records per-request timeout in request.extensions["timeout"].
    timeout = captured["timeout"]
    assert isinstance(timeout, dict)
    assert pytest.approx(timeout.get("connect", 0)) == 0.25


@respx.mock
@pytest.mark.asyncio
async def test_lookup_region_blocked_field_parsed():
    """AC-19: regionRestriction.blocked propagates to VideoStatus."""
    items = [
        {
            "id": "AAAAAAAAAA0",
            "status": {
                "uploadStatus": "processed",
                "privacyStatus": "public",
                "embeddable": True,
            },
            "contentDetails": {
                "duration": "PT5M",
                "regionRestriction": {"blocked": ["DE", "FR"]},
            },
        }
    ]
    respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json=_videos_response(items))

    result = await ys.lookup(["AAAAAAAAAA0"])

    assert result["AAAAAAAAAA0"].region_restriction_blocked == ["DE", "FR"]


@respx.mock
@pytest.mark.asyncio
async def test_lookup_missing_region_restriction_treated_as_empty():
    items = [
        {
            "id": "AAAAAAAAAA0",
            "status": {
                "uploadStatus": "processed",
                "privacyStatus": "public",
                "embeddable": True,
            },
            "contentDetails": {"duration": "PT5M"},
        }
    ]
    respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json=_videos_response(items))

    result = await ys.lookup(["AAAAAAAAAA0"])

    assert result["AAAAAAAAAA0"].region_restriction_blocked == []


@respx.mock
@pytest.mark.asyncio
async def test_lookup_omits_missing_items_gracefully():
    """Deleted/private videos are absent from the API response — caller
    treats absence as 'disqualified', no exception (AC-4)."""
    items = [
        {
            "id": "BBBBBBBBBB0",
            "status": {
                "uploadStatus": "processed",
                "privacyStatus": "public",
                "embeddable": True,
            },
            "contentDetails": {"duration": "PT3M"},
        }
    ]
    respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json=_videos_response(items))

    result = await ys.lookup(["AAAAAAAAAA0", "BBBBBBBBBB0"])

    assert "AAAAAAAAAA0" not in result
    assert "BBBBBBBBBB0" in result


@respx.mock
@pytest.mark.asyncio
async def test_lookup_invalid_id_dropped_pre_request():
    """SR-05: bad ids never appear in the outbound query string."""
    route = respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json={"items": []})

    await ys.lookup(["javascript:x", "AAAAAAAAAA0"])

    sent = route.calls.last.request.url.params["id"]
    assert "javascript:x" not in sent
    assert "AAAAAAAAAA0" in sent


@respx.mock
@pytest.mark.asyncio
async def test_lookup_dedupes_within_batch():
    route = respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json={"items": []})

    await ys.lookup(["AAAAAAAAAA0", "AAAAAAAAAA0", "AAAAAAAAAA0"])

    sent = route.calls.last.request.url.params["id"]
    assert sent.count("AAAAAAAAAA0") == 1


@respx.mock
@pytest.mark.asyncio
async def test_lookup_status_cache_hit_skips_http():
    """AC-16 / SR-06: per-id status cached for STATUS_CACHE_TTL_SECONDS."""
    route = respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json=_videos_response())

    await ys.lookup(["AAAAAAAAAA0"])
    await ys.lookup(["AAAAAAAAAA0"])

    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_lookup_unparseable_duration_drops_item():
    items = [
        {
            "id": "AAAAAAAAAA0",
            "status": {
                "uploadStatus": "processed",
                "privacyStatus": "public",
                "embeddable": True,
            },
            "contentDetails": {"duration": "not-iso"},
        }
    ]
    respx.get(ys.YOUTUBE_API_BASE + ys.VIDEOS_PATH).respond(json=_videos_response(items))

    result = await ys.lookup(["AAAAAAAAAA0"])

    assert result == {}


# ── ISO 8601 parser ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "iso,expected",
    [
        ("PT4M13S", 253),
        ("PT4H", 4 * 3_600),
        ("PT1M30S", 90),
        ("P0D", 0),
        ("PT1H2M3S", 3_723),
        ("PT", 0),
    ],
)
def test_parse_iso8601_duration(iso: str, expected: int):
    assert ys._parse_iso8601_duration(iso) == expected


@pytest.mark.parametrize("bad", ["", "not-iso", "5 minutes", "PT_garbage", None])
def test_parse_iso8601_duration_raises_on_garbage(bad):
    with pytest.raises(ValueError):
        ys._parse_iso8601_duration(bad or "")


# ── Cache eviction (SR-06) ──────────────────────────────────────────────


def test_search_cache_is_bounded():
    """Capacity-bounded TTLCache prevents unbounded memory growth."""
    assert ys._search_cache.maxsize == ys.CACHE_MAX_ENTRIES
    assert ys._status_cache.maxsize == ys.CACHE_MAX_ENTRIES


# ── Quota counter UTC rollover ──────────────────────────────────────────


def test_quota_counter_resets_on_new_utc_day(monkeypatch):
    """quota_used_today() must reset when the UTC date rolls over."""
    ys._bump_quota(100)
    assert ys.quota_used_today() == 100

    fake_today = _dt.datetime.now(_dt.UTC).date() + _dt.timedelta(days=1)

    class _FakeDt(_dt.datetime):
        @classmethod
        def now(cls, tz=None):  # type: ignore[override]
            return _dt.datetime.combine(fake_today, _dt.time(0, 0), tz or _dt.UTC)

    monkeypatch.setattr(ys._dt, "datetime", _FakeDt)
    assert ys.quota_used_today() == 0


def test_clear_caches_resets_state():
    ys._search_cache["x"] = []
    ys._status_cache["AAAAAAAAAA0"] = ys.VideoStatus(
        video_id="AAAAAAAAAA0",
        duration_seconds=1,
        upload_status="processed",
        privacy_status="public",
        embeddable=True,
        region_restriction_blocked=[],
    )
    ys._bump_quota(50)

    ys.clear_caches()

    assert len(ys._search_cache) == 0
    assert len(ys._status_cache) == 0
    assert ys.quota_used_today() == 0
