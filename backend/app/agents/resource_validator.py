"""Post-generation validator that HTTP-probes learning plan resource URLs.

Inserted between ``generate_plan`` and ``END`` in the assessment pipeline.
Pure-Python — no LLM calls.  Nulls out unreachable or error-page URLs so the
frontend renders titles as plain text instead of broken links.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
import time
from urllib.parse import urlparse

import httpx

from app.graph.state import AssessmentState, LearningPlan

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

_MAX_CONCURRENT = 10
_TIMEOUT_SECONDS = 5.0
_CACHE_TTL_SECONDS = 3600  # 1 hour
_MAX_BODY_BYTES = 4096  # soft-404 detection snippet size

# ── SSRF prevention ─────────────────────────────────────────────────────


def _is_ssrf_target(url: str) -> bool:
    """Return True if the URL targets a private/internal address."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        return True

    hostname = parsed.hostname
    if not hostname:
        return True

    # Block single-label hostnames (e.g. Docker service names: db, backend)
    if "." not in hostname and ":" not in hostname:
        return True

    try:
        addr_infos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        # DNS resolution failed — treat as unreachable, not SSRF
        return False

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip = ipaddress.ip_address(sockaddr[0])

        # Normalize IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) to plain IPv4
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped

        # Use stdlib checks to catch all non-global addresses, including
        # ranges not explicitly listed in _BLOCKED_NETWORKS
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return True

    return False


# ── Soft-404 detection ───────────────────────────────────────────────────

_SOFT_404_TITLE = re.compile(
    r"<title[^>]*>\s*("
    r"404|page\s*not\s*found|not\s*found|error\s*\d{3}|error\s*page|server\s*error|"
    r"oops|sorry.*?doesn.?t\s*exist|no\s*longer\s*available|"
    r"this\s*page\s*(has\s*been\s*removed|doesn.?t\s*exist|is\s*unavailable)"
    r")\s*[|<\-\u2013\u2014]",
    re.IGNORECASE,
)

_SOFT_404_NOINDEX = re.compile(
    r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\'][^"\']*noindex',
    re.IGNORECASE,
)


def _is_soft_404(body: str) -> bool:
    """Detect pages that return 200 but are actually error pages."""
    snippet = body[:_MAX_BODY_BYTES]
    if _SOFT_404_TITLE.search(snippet):
        return True
    return bool(_SOFT_404_NOINDEX.search(snippet))


# ── URL cache ────────────────────────────────────────────────────────────

_url_cache: dict[str, tuple[bool, float]] = {}


def _get_cached(url: str) -> bool | None:
    entry = _url_cache.get(url)
    if entry and (time.monotonic() - entry[1]) < _CACHE_TTL_SECONDS:
        return entry[0]
    return None


def _set_cached(url: str, reachable: bool) -> None:
    _url_cache[url] = (reachable, time.monotonic())


def clear_url_cache() -> None:
    """Clear the URL validation cache. Used by tests."""
    _url_cache.clear()


# ── HTTP probing ─────────────────────────────────────────────────────────

_MAX_REDIRECTS = 10


async def _follow_redirects(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: object,
) -> httpx.Response:
    """Manually follow redirects, validating each hop against SSRF rules.

    Unlike httpx's built-in ``follow_redirects=True`` this validates each
    ``Location`` target *before* making the request, so we never connect
    to an internal host even as an intermediate redirect.
    """
    current_url = url
    for _ in range(_MAX_REDIRECTS):
        r = await client.request(method, current_url, follow_redirects=False, **kwargs)
        if r.is_redirect and r.has_redirect_location:
            next_url = str(r.headers["location"])
            # Resolve relative redirects
            if not next_url.startswith(("http://", "https://")):
                next_url = str(r.url.join(next_url))
            if await asyncio.to_thread(_is_ssrf_target, next_url):
                logger.info("resource_validator.ssrf_redirect url=%s hop=%s", url, next_url)
                return r  # Return the redirect response; caller sees non-200
            current_url = next_url
        else:
            return r
    return r  # Max redirects reached — return last response


async def _get_body_limited(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """GET a URL with SSRF-safe redirects for soft-404 body inspection.

    Uses ``_follow_redirects`` to validate each hop.  Body truncation is
    handled downstream by ``_is_soft_404`` (slices to ``_MAX_BODY_BYTES``).
    """
    return await _follow_redirects(client, "GET", url, timeout=_TIMEOUT_SECONDS)


async def _check_url(url: str, client: httpx.AsyncClient) -> bool:
    """Return True if *url* is reachable and not an error page."""
    try:
        r = await _follow_redirects(
            client,
            "HEAD",
            url,
            timeout=_TIMEOUT_SECONDS,
        )

        if r.is_redirect:
            # Redirect chain ended at SSRF target or max redirects
            return False

        if r.status_code >= 400:
            # Some servers reject HEAD — fall back to GET with Range header
            r = await _follow_redirects(
                client,
                "GET",
                url,
                timeout=_TIMEOUT_SECONDS,
                headers={"Range": "bytes=0-0"},
            )
            if r.is_redirect:
                return False

        if r.status_code >= 400:
            logger.info("resource_validator.http_error url=%s status=%d", url, r.status_code)
            return False

        # Soft-404 detection on HTML responses
        content_type = r.headers.get("content-type", "")
        if content_type.startswith("text/html"):
            # HEAD responses have no body — need a limited GET for inspection
            if r.request.method == "HEAD" or not r.content:
                r = await _get_body_limited(client, url)
                if r.is_redirect or r.status_code >= 400:
                    return False

            if _is_soft_404(r.text):
                logger.info("resource_validator.soft_404 url=%s", url)
                return False

        return True
    except (httpx.HTTPError, httpx.TimeoutException):
        return False
    except Exception:
        # Fail-open: unexpected errors preserve the URL rather than nulling it
        logger.warning("resource_validator.probe_failed url=%s", url, exc_info=True)
        return True


async def _check_with_cache(
    url: str, client: httpx.AsyncClient, sem: asyncio.Semaphore
) -> tuple[str, bool]:
    """Check a URL with cache and semaphore. Returns (url, is_valid)."""
    cached = _get_cached(url)
    if cached is not None:
        logger.debug("resource_validator.cache_hit url=%s result=%s", url, cached)
        return url, cached

    # SSRF check (runs DNS resolution, so do it under the semaphore)
    async with sem:
        is_blocked = await asyncio.to_thread(_is_ssrf_target, url)
        if is_blocked:
            logger.info("resource_validator.ssrf_blocked url=%s", url)
            _set_cached(url, False)
            return url, False

        result = await _check_url(url, client)

    _set_cached(url, result)
    return url, result


# ── Graph node ───────────────────────────────────────────────────────────


async def validate_resources(state: AssessmentState) -> dict:
    """Validate resource URLs in the learning plan; null out unreachable ones."""
    plan: LearningPlan | None = state.get("learning_plan")
    if not plan or not plan.phases:
        return {}

    # Collect unique URLs from all concepts across all phases
    urls: list[str] = []
    seen_urls: set[str] = set()
    for phase in plan.phases:
        for concept in phase.concepts:
            for resource in concept.resources:
                if resource.url and resource.url not in seen_urls:
                    urls.append(resource.url)
                    seen_urls.add(resource.url)

    if not urls:
        return {}

    logger.info("resource_validator.start total=%d", len(urls))

    sem = asyncio.Semaphore(_MAX_CONCURRENT)
    async with httpx.AsyncClient(
        follow_redirects=False,  # Redirects followed manually with per-hop SSRF checks
        timeout=_TIMEOUT_SECONDS,
        limits=httpx.Limits(max_connections=_MAX_CONCURRENT),
        headers={"User-Agent": "OpenLearning-LinkChecker/1.0"},
    ) as client:
        results = await asyncio.gather(
            *[_check_with_cache(url, client, sem) for url in urls],
            return_exceptions=True,
        )

    # Build url -> is_valid lookup from results
    url_validity: dict[str, bool] = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        url, is_valid = result
        url_validity[url] = is_valid

    # Null out failed URLs across ALL concepts (handles duplicates)
    nulled = 0
    for phase in plan.phases:
        for concept in phase.concepts:
            for resource in concept.resources:
                if resource.url and not url_validity.get(resource.url, True):
                    logger.info(
                        "resource_validator.nulled url=%s phase=%s concept=%s",
                        resource.url,
                        phase.title,
                        concept.name,
                    )
                    resource.url = None
                    nulled += 1

    if nulled:
        logger.info("resource_validator.summary total=%d nulled=%d", len(urls), nulled)

    return {"learning_plan": plan}
