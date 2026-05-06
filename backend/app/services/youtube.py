"""YouTube Data API v3 client for the video-enrichment pipeline (issue #177).

Owns all HTTP I/O against ``googleapis.com/youtube/v3`` plus the bounded TTL
caches.  Exposes :func:`search` and :func:`lookup` — the only consumers of
the API key.  All semantic concerns (sanitization, relevance, plan mutation)
live in :mod:`app.agents.video_enricher`.

Security contract (api-contracts.md §1.4): SecretStr read at request time
only; ``YouTubeAPIError`` repr never carries URL/key (SR-01); ``videoId``
regex-validated before any cache write or return (SR-05); httpx
``follow_redirects=False`` (SR-09); per-request Timeout (SR-04).
"""

from __future__ import annotations

import datetime as _dt
import logging
import re
from typing import Any

import httpx
from cachetools import TTLCache
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)


# ── Public constants (frozen by api-contracts.md §1.1) ──────────────────

YOUTUBE_API_BASE: str = "https://www.googleapis.com/youtube/v3"
SEARCH_PATH: str = "/search"
VIDEOS_PATH: str = "/videos"
SEARCH_CACHE_TTL_SECONDS: int = 86_400  # 24h
STATUS_CACHE_TTL_SECONDS: int = 21_600  # 6h
CACHE_MAX_ENTRIES: int = 1_000  # SR-06
# Per-request httpx timeout is read from Settings at request time (SR-04);
# the default below is for documentation only.
PER_REQUEST_TIMEOUT_SECONDS_DEFAULT: float = 10.0
SEARCH_RESULTS_PER_QUERY: int = 5
VIDEOS_BATCH_SIZE: int = 50
# 11-char base64url-safe id (SR-05) — XSS / URL-injection defence.
VIDEO_ID_REGEX: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_-]{11}$")


# ── Public data types ───────────────────────────────────────────────────


class VideoCandidate(BaseModel):
    """Result of a search.list query — a single candidate video."""

    video_id: str
    title: str
    channel_title: str
    live_broadcast_content: str  # "none" | "live" | "upcoming"


class VideoStatus(BaseModel):
    """Result of a videos.list lookup — disqualifier inputs."""

    video_id: str
    duration_seconds: int  # parsed from contentDetails.duration ISO 8601
    upload_status: str
    privacy_status: str
    embeddable: bool
    region_restriction_blocked: list[str]


class YouTubeAPIError(Exception):
    """Raised on any non-success outcome of a YouTube API call.

    ``__repr__``/``__str__`` are overridden so the URL and key cannot leak
    via logging frameworks that call repr() (SR-01 / T-07).
    """

    def __init__(self, status_code: int, retry_after_seconds: int | None) -> None:
        super().__init__(f"youtube_api_error status={status_code}")
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds

    def __repr__(self) -> str:
        return (
            f"YouTubeAPIError(status_code={self.status_code}, "
            f"retry_after_seconds={self.retry_after_seconds})"
        )

    def __str__(self) -> str:
        return self.__repr__()


# ── Caches + quota counter (module-local, reset by clear_caches()) ──────


_search_cache: TTLCache[str, list[VideoCandidate]] = TTLCache(
    maxsize=CACHE_MAX_ENTRIES, ttl=SEARCH_CACHE_TTL_SECONDS
)
_status_cache: TTLCache[str, VideoStatus] = TTLCache(
    maxsize=CACHE_MAX_ENTRIES, ttl=STATUS_CACHE_TTL_SECONDS
)
# Daily quota bookkeeping — process-local; resets at UTC midnight.
_quota_used: int = 0
_quota_date: _dt.date = _dt.datetime.now(_dt.UTC).date()


def _bump_quota(units: int) -> None:
    """Add *units* to today's counter, rolling over on UTC date change."""
    global _quota_used, _quota_date
    today = _dt.datetime.now(_dt.UTC).date()
    if today != _quota_date:
        _quota_used, _quota_date = 0, today
    _quota_used += units


def quota_used_today() -> int:
    """Units spent today (UTC) — feeds the circuit breaker in the caller."""
    today = _dt.datetime.now(_dt.UTC).date()
    return _quota_used if today == _quota_date else 0


def clear_caches() -> None:
    """Test helper — reset caches and the daily quota counter."""
    global _quota_used, _quota_date
    _search_cache.clear()
    _status_cache.clear()
    _quota_used = 0
    _quota_date = _dt.datetime.now(_dt.UTC).date()


# ── ISO 8601 duration parser (small, exact subset YouTube emits) ────────

_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def _parse_iso8601_duration(text: str) -> int:
    """Return whole seconds; raises :class:`ValueError` on malformed input."""
    m = _ISO_DURATION_RE.match(text or "")
    if not m:
        raise ValueError(f"unparseable duration: {text!r}")
    d, h, mi, s = (int(m[k] or 0) for k in ("days", "hours", "minutes", "seconds"))
    return d * 86_400 + h * 3_600 + mi * 60 + s


# ── Internal HTTP helpers ───────────────────────────────────────────────


def _api_key() -> str:
    """Read the API key fresh on every call — never cache it (SR-01)."""
    return get_settings().youtube_api_key.get_secret_value()


async def _request(path: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET against YouTube Data API v3, mapping every non-2xx to
    :class:`YouTubeAPIError`.  Never logs URL/key (SR-01 / SR-07)."""
    # Module-supplied key always wins so a caller cannot accidentally (or
    # maliciously) shadow the credential by passing ``key`` in *params*
    # (SR-01 / Copilot review).
    params = {**params, "key": _api_key()}
    timeout = httpx.Timeout(get_settings().youtube_per_request_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(YOUTUBE_API_BASE + path, params=params)
    except (httpx.TimeoutException, httpx.HTTPError) as exc:
        logger.warning("youtube.api_error status=0 retry_after=None")
        raise YouTubeAPIError(0, None) from exc

    if response.status_code >= 400:
        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        logger.warning(
            "youtube.api_error status=%d retry_after=%s",
            response.status_code,
            retry_after,
        )
        raise YouTubeAPIError(response.status_code, retry_after)
    return response.json()


def _parse_retry_after(header: str | None) -> int | None:
    """Best-effort parse of the ``Retry-After`` header (seconds form only)."""
    if not header:
        return None
    try:
        return int(header)
    except (TypeError, ValueError):
        return None


# ── Public API ──────────────────────────────────────────────────────────


async def search(query: str) -> list[VideoCandidate]:
    """Return up to :data:`SEARCH_RESULTS_PER_QUERY` candidates whose
    ``videoId`` matches :data:`VIDEO_ID_REGEX`.  Query is treated as already
    sanitized (caller owns SR-02 / SR-11).  Quota: 100 units per cache miss.
    """
    cached = _search_cache.get(query)
    if cached is not None:
        return cached

    payload = await _request(
        SEARCH_PATH,
        {
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": SEARCH_RESULTS_PER_QUERY,
            "videoEmbeddable": "true",
            "safeSearch": "moderate",
            "relevanceLanguage": "en",
        },
    )
    _bump_quota(100)

    candidates = [c for c in (_parse_search_item(item) for item in payload.get("items", [])) if c]
    _search_cache[query] = candidates
    return candidates


def _parse_search_item(item: dict[str, Any]) -> VideoCandidate | None:
    """``None`` if the videoId fails the regex check (SR-05)."""
    video_id = (item.get("id") or {}).get("videoId", "")
    if not VIDEO_ID_REGEX.match(video_id):
        return None
    snip = item.get("snippet") or {}
    return VideoCandidate(
        video_id=video_id,
        title=snip.get("title", ""),
        channel_title=snip.get("channelTitle", ""),
        live_broadcast_content=snip.get("liveBroadcastContent", "none"),
    )


async def lookup(video_ids: list[str]) -> dict[str, VideoStatus]:
    """Batched ``videos.list`` → ``video_id -> VideoStatus``.  Dupes/regex-invalid
    dropped, empty input returns ``{}`` (no HTTP).  Quota: 1/batched call ≤50 ids.
    Deleted/private videos are absent (caller treats absence as disqualified)."""
    unique_ids = _dedupe_video_ids(video_ids)
    if not unique_ids:
        return {}

    result: dict[str, VideoStatus] = {}

    # Serve from cache where possible; collect cache misses for batched fetch.
    misses: list[str] = []
    for vid in unique_ids:
        cached = _status_cache.get(vid)
        if cached is not None:
            result[vid] = cached
        else:
            misses.append(vid)

    for batch_start in range(0, len(misses), VIDEOS_BATCH_SIZE):
        batch = misses[batch_start : batch_start + VIDEOS_BATCH_SIZE]
        payload = await _request(
            VIDEOS_PATH,
            {"id": ",".join(batch), "part": "status,contentDetails"},
        )
        _bump_quota(1)
        for item in payload.get("items", []):
            status = _parse_video_item(item)
            if status is None:
                continue
            _status_cache[status.video_id] = status
            result[status.video_id] = status

    return result


def _dedupe_video_ids(video_ids: list[str]) -> list[str]:
    """Return distinct, regex-valid ids in input order."""
    seen: set[str] = set()
    out: list[str] = []
    for vid in video_ids:
        if vid in seen or not VIDEO_ID_REGEX.match(vid):
            continue
        seen.add(vid)
        out.append(vid)
    return out


def _parse_video_item(item: dict[str, Any]) -> VideoStatus | None:
    """``None`` if id fails regex or duration is unparseable."""
    video_id = item.get("id", "")
    if not VIDEO_ID_REGEX.match(video_id):
        return None
    st = item.get("status") or {}
    cd = item.get("contentDetails") or {}
    try:
        duration = _parse_iso8601_duration(cd.get("duration", ""))
    except ValueError:
        return None
    return VideoStatus(
        video_id=video_id,
        duration_seconds=duration,
        upload_status=st.get("uploadStatus", ""),
        privacy_status=st.get("privacyStatus", ""),
        embeddable=bool(st.get("embeddable", False)),
        region_restriction_blocked=list((cd.get("regionRestriction") or {}).get("blocked") or []),
    )
