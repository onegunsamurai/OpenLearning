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

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


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
        for network in _BLOCKED_NETWORKS:
            if ip in network:
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


async def _is_redirect_to_internal(response: httpx.Response) -> bool:
    """Check if a redirect chain led to an internal/private IP.

    Runs DNS resolution in a thread to avoid blocking the event loop.
    """
    if response.history:
        final_url = str(response.url)
        # _is_ssrf_target calls socket.getaddrinfo (blocking) — offload it
        return await asyncio.to_thread(_is_ssrf_target, final_url)
    return False


async def _check_url(url: str, client: httpx.AsyncClient) -> bool:
    """Return True if *url* is reachable and not an error page."""
    try:
        r = await client.head(url, follow_redirects=True, timeout=_TIMEOUT_SECONDS)

        # SSRF: check if redirects led to an internal IP
        if await _is_redirect_to_internal(r):
            logger.info("resource_validator.ssrf_redirect url=%s final=%s", url, r.url)
            return False

        if r.status_code >= 400:
            # Some servers reject HEAD — fall back to GET with Range header
            r = await client.get(
                url,
                follow_redirects=True,
                timeout=_TIMEOUT_SECONDS,
                headers={"Range": "bytes=0-0"},
            )
            if await _is_redirect_to_internal(r):
                logger.info("resource_validator.ssrf_redirect url=%s final=%s", url, r.url)
                return False

        if r.status_code >= 400:
            logger.info("resource_validator.http_error url=%s status=%d", url, r.status_code)
            return False

        # Soft-404 detection on HTML responses
        content_type = r.headers.get("content-type", "")
        if content_type.startswith("text/html"):
            # HEAD responses have no body — need a GET for content inspection
            if r.request.method == "HEAD" or not r.content:
                r = await client.get(
                    url,
                    follow_redirects=True,
                    timeout=_TIMEOUT_SECONDS,
                )
                if await _is_redirect_to_internal(r):
                    logger.info("resource_validator.ssrf_redirect url=%s final=%s", url, r.url)
                    return False
                if r.status_code >= 400:
                    logger.info(
                        "resource_validator.http_error url=%s status=%d", url, r.status_code
                    )
                    return False

            if _is_soft_404(r.text):
                logger.info("resource_validator.soft_404 url=%s", url)
                return False

        return True
    except (httpx.HTTPError, httpx.TimeoutException):
        return False
    except Exception:
        logger.warning("resource_validator.probe_failed url=%s", url, exc_info=True)
        return False


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

    # Collect (phase_idx, resource_idx, url) for all non-null URLs
    targets: list[tuple[int, int, str]] = []
    seen_urls: set[str] = set()
    for pi, phase in enumerate(plan.phases):
        for ri, resource in enumerate(phase.resources):
            if resource.url and resource.url not in seen_urls:
                targets.append((pi, ri, resource.url))
                seen_urls.add(resource.url)

    if not targets:
        return {}

    logger.info("resource_validator.start total=%d", len(targets))

    sem = asyncio.Semaphore(_MAX_CONCURRENT)
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=_TIMEOUT_SECONDS,
        limits=httpx.Limits(max_connections=_MAX_CONCURRENT),
        headers={"User-Agent": "OpenLearning-LinkChecker/1.0"},
    ) as client:
        results = await asyncio.gather(
            *[_check_with_cache(url, client, sem) for _, _, url in targets],
            return_exceptions=True,
        )

    # Build url -> is_valid lookup from results
    url_validity: dict[str, bool] = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        url, is_valid = result
        url_validity[url] = is_valid

    # Null out failed URLs across ALL phases (handles duplicates across phases)
    nulled = 0
    for phase in plan.phases:
        for resource in phase.resources:
            if resource.url and not url_validity.get(resource.url, True):
                logger.info(
                    "resource_validator.nulled url=%s phase=%s",
                    resource.url,
                    phase.title,
                )
                resource.url = None
                nulled += 1

    if nulled:
        logger.info("resource_validator.summary total=%d nulled=%d", len(targets), nulled)

    return {"learning_plan": plan}
