"""Tests for the resource URL validator pipeline node."""

from __future__ import annotations

import asyncio
import socket
import time
from unittest.mock import patch

import httpx
import pytest
import respx

from app.agents.resource_validator import (
    _CACHE_TTL_SECONDS,
    _check_url,
    _is_soft_404,
    _is_ssrf_target,
    _url_cache,
    clear_url_cache,
    validate_resources,
)
from app.graph.state import LearningPhase, LearningPlan, Resource


@pytest.fixture(autouse=True)
def _clean_cache():
    """Ensure a clean URL cache for every test."""
    clear_url_cache()
    yield
    clear_url_cache()


def _make_plan(*phase_resources: list[Resource]) -> LearningPlan:
    """Build a minimal LearningPlan with the given resources per phase."""
    phases = []
    for i, resources in enumerate(phase_resources, start=1):
        phases.append(
            LearningPhase(
                phase_number=i,
                title=f"Phase {i}",
                concepts=[f"concept-{i}"],
                rationale="test",
                resources=resources,
                estimated_hours=1.0,
            )
        )
    return LearningPlan(phases=phases, total_hours=float(len(phases)), summary="test plan")


def _make_state(plan: LearningPlan | None = None) -> dict:
    """Build a minimal state dict with the given plan."""
    state: dict = {}
    if plan is not None:
        state["learning_plan"] = plan
    return state


# ── _is_soft_404 tests ──────────────────────────────────────────────────


class TestIsSoft404:
    def test_title_with_404(self):
        html = "<html><head><title>404 | Example</title></head></html>"
        assert _is_soft_404(html) is True

    def test_title_page_not_found(self):
        html = "<html><head><title>Page Not Found - Example</title></head></html>"
        assert _is_soft_404(html) is True

    def test_title_not_found(self):
        html = "<html><head><title>Not Found | Site</title></head></html>"
        assert _is_soft_404(html) is True

    def test_title_oops(self):
        html = "<html><head><title>Oops | Site</title></head></html>"
        assert _is_soft_404(html) is True

    def test_title_no_longer_available(self):
        html = "<html><head><title>No longer available - Site</title></head></html>"
        assert _is_soft_404(html) is True

    def test_title_page_removed(self):
        html = "<html><head><title>This page has been removed | Site</title></head></html>"
        assert _is_soft_404(html) is True

    def test_meta_noindex(self):
        html = '<html><head><meta name="robots" content="noindex, nofollow"></head></html>'
        assert _is_soft_404(html) is True

    def test_normal_page_not_flagged(self):
        html = "<html><head><title>React Hooks Tutorial | Learn React</title></head></html>"
        assert _is_soft_404(html) is False

    def test_tutorial_about_404_errors_not_flagged(self):
        """Title mentioning 404 mid-sentence won't match because the pattern
        requires error text at the START of the title, followed by a separator."""
        html = "<html><head><title>Handling 404 Errors in React | Blog</title></head></html>"
        assert _is_soft_404(html) is False

    def test_empty_body_not_flagged(self):
        assert _is_soft_404("") is False

    def test_only_inspects_first_4kb(self):
        html = "x" * 5000 + "<title>404 | Not Found</title>"
        assert _is_soft_404(html) is False


# ── _is_ssrf_target tests ───────────────────────────────────────────────


class TestIsSSRFTarget:
    def test_private_ip_10(self):
        with patch(
            "app.agents.resource_validator.socket.getaddrinfo",
            return_value=[
                (2, 1, 6, "", ("10.0.0.1", 0)),
            ],
        ):
            assert _is_ssrf_target("http://internal.example.com/") is True

    def test_private_ip_172(self):
        with patch(
            "app.agents.resource_validator.socket.getaddrinfo",
            return_value=[
                (2, 1, 6, "", ("172.16.0.1", 0)),
            ],
        ):
            assert _is_ssrf_target("http://internal.example.com/") is True

    def test_private_ip_192(self):
        with patch(
            "app.agents.resource_validator.socket.getaddrinfo",
            return_value=[
                (2, 1, 6, "", ("192.168.1.1", 0)),
            ],
        ):
            assert _is_ssrf_target("http://internal.example.com/") is True

    def test_loopback(self):
        with patch(
            "app.agents.resource_validator.socket.getaddrinfo",
            return_value=[
                (2, 1, 6, "", ("127.0.0.1", 0)),
            ],
        ):
            assert _is_ssrf_target("http://localhost.example.com/") is True

    def test_link_local_169(self):
        with patch(
            "app.agents.resource_validator.socket.getaddrinfo",
            return_value=[
                (2, 1, 6, "", ("169.254.169.254", 0)),
            ],
        ):
            assert _is_ssrf_target("http://metadata.example.com/") is True

    def test_public_ip_allowed(self):
        with patch(
            "app.agents.resource_validator.socket.getaddrinfo",
            return_value=[
                (2, 1, 6, "", ("93.184.216.34", 0)),
            ],
        ):
            assert _is_ssrf_target("https://example.com/") is False

    def test_non_http_scheme_blocked(self):
        assert _is_ssrf_target("ftp://example.com/file") is True

    def test_no_scheme_blocked(self):
        assert _is_ssrf_target("example.com/page") is True

    def test_single_label_hostname_blocked(self):
        """Docker service names like 'db' or 'backend' are single-label."""
        assert _is_ssrf_target("http://db/") is True
        assert _is_ssrf_target("http://backend/") is True

    def test_dns_failure_not_treated_as_ssrf(self):
        """DNS failure means unreachable, not malicious — let _check_url handle it."""
        with patch(
            "app.agents.resource_validator.socket.getaddrinfo",
            side_effect=socket.gaierror("DNS failed"),
        ):
            assert _is_ssrf_target("https://nonexistent.example.com/") is False

    def test_ipv6_loopback_blocked(self):
        with patch(
            "app.agents.resource_validator.socket.getaddrinfo",
            return_value=[
                (10, 1, 6, "", ("::1", 0, 0, 0)),
            ],
        ):
            assert _is_ssrf_target("http://ipv6host.example.com/") is True

    def test_no_hostname(self):
        assert _is_ssrf_target("http://") is True


# ── _check_url tests ────────────────────────────────────────────────────


class TestCheckUrl:
    @pytest.mark.asyncio
    @respx.mock
    async def test_200_valid_page_preserved(self):
        respx.head("https://example.com/docs").mock(
            return_value=httpx.Response(200, headers={"content-type": "text/html"}),
        )
        respx.get("https://example.com/docs").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><head><title>Docs | Example</title></head></html>",
            ),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/docs", client) is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_404_returns_false(self):
        respx.head("https://example.com/gone").mock(
            return_value=httpx.Response(404),
        )
        respx.get("https://example.com/gone").mock(
            return_value=httpx.Response(404),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/gone", client) is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_500_returns_false(self):
        respx.head("https://example.com/broken").mock(
            return_value=httpx.Response(500),
        )
        respx.get("https://example.com/broken").mock(
            return_value=httpx.Response(500),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/broken", client) is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_403_returns_false(self):
        respx.head("https://example.com/private").mock(
            return_value=httpx.Response(403),
        )
        respx.get("https://example.com/private").mock(
            return_value=httpx.Response(403),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/private", client) is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_head_rejected_get_fallback(self):
        """Server returns 405 on HEAD, but 200 on GET — URL should be valid."""
        respx.head("https://example.com/nohead").mock(
            return_value=httpx.Response(405),
        )
        respx.get("https://example.com/nohead").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "application/json"},
                text="{}",
            ),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/nohead", client) is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_soft_404_title_detected(self):
        """200 response with 'Page Not Found' in title should fail."""
        respx.head("https://example.com/soft404").mock(
            return_value=httpx.Response(200, headers={"content-type": "text/html"}),
        )
        respx.get("https://example.com/soft404").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><head><title>Page Not Found | Example</title></head></html>",
            ),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/soft404", client) is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_soft_404_noindex_detected(self):
        """200 response with meta noindex should fail."""
        respx.head("https://example.com/noindex").mock(
            return_value=httpx.Response(200, headers={"content-type": "text/html"}),
        )
        respx.get("https://example.com/noindex").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text='<html><head><meta name="robots" content="noindex"></head></html>',
            ),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/noindex", client) is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_non_html_skips_soft_404(self):
        """Non-HTML content types skip soft-404 detection."""
        respx.head("https://example.com/api.json").mock(
            return_value=httpx.Response(200, headers={"content-type": "application/json"}),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/api.json", client) is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_timeout_returns_false(self):
        respx.head("https://example.com/slow").mock(
            side_effect=httpx.ReadTimeout("timeout"),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/slow", client) is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_connect_error_returns_false(self):
        respx.head("https://example.com/down").mock(
            side_effect=httpx.ConnectError("connection refused"),
        )
        async with httpx.AsyncClient() as client:
            assert await _check_url("https://example.com/down", client) is False

    @pytest.mark.asyncio
    @respx.mock
    async def test_redirect_to_internal_ip_blocked(self):
        """URL that redirects to an internal IP should be treated as invalid."""
        respx.head("https://example.com/redirect").mock(
            return_value=httpx.Response(
                301,
                headers={"location": "http://internal.example.com/"},
            ),
        )
        respx.head("http://internal.example.com/").mock(
            return_value=httpx.Response(200, headers={"content-type": "text/plain"}),
        )
        async with httpx.AsyncClient(follow_redirects=True) as client:
            with patch(
                "app.agents.resource_validator._is_ssrf_target",
                side_effect=lambda url: "internal" in url,
            ):
                assert await _check_url("https://example.com/redirect", client) is False


# ── Cache tests ──────────────────────────────────────────────────────────


class TestCache:
    def test_cache_hit(self):
        from app.agents.resource_validator import _get_cached, _set_cached

        _set_cached("https://example.com/", True)
        assert _get_cached("https://example.com/") is True

    def test_cache_miss(self):
        from app.agents.resource_validator import _get_cached

        assert _get_cached("https://unknown.com/") is None

    def test_cache_expired(self):
        from app.agents.resource_validator import _get_cached

        _url_cache["https://old.com/"] = (True, time.monotonic() - _CACHE_TTL_SECONDS - 1)
        assert _get_cached("https://old.com/") is None

    def test_clear_cache(self):
        from app.agents.resource_validator import _get_cached, _set_cached

        _set_cached("https://example.com/", True)
        clear_url_cache()
        assert _get_cached("https://example.com/") is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_cached_url_skips_network(self):
        """A cached-valid URL should not trigger HTTP requests."""
        from app.agents.resource_validator import _set_cached

        _set_cached("https://cached.example.com/docs", True)

        plan = _make_plan(
            [
                Resource(type="article", title="Cached", url="https://cached.example.com/docs"),
            ]
        )
        state = _make_state(plan)

        with patch("app.agents.resource_validator._is_ssrf_target", return_value=False):
            result = await validate_resources(state)

        assert (
            result["learning_plan"].phases[0].resources[0].url == "https://cached.example.com/docs"
        )


# ── validate_resources integration tests ─────────────────────────────────


class TestValidateResources:
    @pytest.mark.asyncio
    async def test_no_plan_returns_empty(self):
        state = _make_state(None)
        result = await validate_resources(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_phases_returns_empty(self):
        plan = LearningPlan(phases=[], total_hours=0, summary="empty")
        state = _make_state(plan)
        result = await validate_resources(state)
        assert result == {}

    @pytest.mark.asyncio
    async def test_no_urls_returns_empty(self):
        plan = _make_plan([Resource(type="article", title="No URL")])
        state = _make_state(plan)
        result = await validate_resources(state)
        assert result == {}

    @pytest.mark.asyncio
    @respx.mock
    async def test_valid_url_preserved(self):
        respx.head("https://react.dev/learn").mock(
            return_value=httpx.Response(200, headers={"content-type": "text/html"}),
        )
        respx.get("https://react.dev/learn").mock(
            return_value=httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><head><title>React Learn | React</title></head></html>",
            ),
        )

        plan = _make_plan(
            [
                Resource(type="docs", title="React Docs", url="https://react.dev/learn"),
            ]
        )
        state = _make_state(plan)

        with patch("app.agents.resource_validator._is_ssrf_target", return_value=False):
            result = await validate_resources(state)

        assert result["learning_plan"].phases[0].resources[0].url == "https://react.dev/learn"

    @pytest.mark.asyncio
    @respx.mock
    async def test_404_url_nulled_title_preserved(self):
        respx.head("https://dead.example.com/page").mock(
            return_value=httpx.Response(404),
        )
        respx.get("https://dead.example.com/page").mock(
            return_value=httpx.Response(404),
        )

        plan = _make_plan(
            [
                Resource(type="article", title="Dead Link", url="https://dead.example.com/page"),
            ]
        )
        state = _make_state(plan)

        with patch("app.agents.resource_validator._is_ssrf_target", return_value=False):
            result = await validate_resources(state)

        resource = result["learning_plan"].phases[0].resources[0]
        assert resource.url is None
        assert resource.title == "Dead Link"
        assert resource.type == "article"

    @pytest.mark.asyncio
    @respx.mock
    async def test_mix_of_valid_and_invalid(self):
        respx.head("https://good.example.com/").mock(
            return_value=httpx.Response(200, headers={"content-type": "application/json"}),
        )
        respx.head("https://bad.example.com/").mock(
            return_value=httpx.Response(404),
        )
        respx.get("https://bad.example.com/").mock(
            return_value=httpx.Response(404),
        )

        plan = _make_plan(
            [
                Resource(type="article", title="Good", url="https://good.example.com/"),
                Resource(type="article", title="Bad", url="https://bad.example.com/"),
                Resource(type="guide", title="No URL"),
            ]
        )
        state = _make_state(plan)

        with patch("app.agents.resource_validator._is_ssrf_target", return_value=False):
            result = await validate_resources(state)

        resources = result["learning_plan"].phases[0].resources
        assert resources[0].url == "https://good.example.com/"
        assert resources[1].url is None
        assert resources[2].url is None  # was None, stays None

    @pytest.mark.asyncio
    @respx.mock
    async def test_ssrf_blocked_url_nulled(self):
        plan = _make_plan(
            [
                Resource(type="article", title="Internal", url="http://db:5432/"),
            ]
        )
        state = _make_state(plan)

        # _is_ssrf_target returns True for single-label hostnames
        result = await validate_resources(state)

        resource = result["learning_plan"].phases[0].resources[0]
        assert resource.url is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_duplicate_urls_validated_once(self):
        """Same URL across phases should only be probed once."""
        call_count = 0

        async def _counting_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, headers={"content-type": "application/json"})

        respx.head("https://example.com/shared").mock(side_effect=_counting_handler)

        plan = _make_plan(
            [Resource(type="article", title="A", url="https://example.com/shared")],
            [Resource(type="article", title="B", url="https://example.com/shared")],
        )
        state = _make_state(plan)

        with patch("app.agents.resource_validator._is_ssrf_target", return_value=False):
            result = await validate_resources(state)

        assert call_count == 1
        assert result["learning_plan"].phases[0].resources[0].url == "https://example.com/shared"
        assert result["learning_plan"].phases[1].resources[0].url == "https://example.com/shared"

    @pytest.mark.asyncio
    @respx.mock
    async def test_duplicate_invalid_urls_both_nulled(self):
        """Same invalid URL across phases should be nulled in both."""
        respx.head("https://example.com/dead").mock(
            return_value=httpx.Response(404),
        )
        respx.get("https://example.com/dead").mock(
            return_value=httpx.Response(404),
        )

        plan = _make_plan(
            [Resource(type="article", title="A", url="https://example.com/dead")],
            [Resource(type="article", title="B", url="https://example.com/dead")],
        )
        state = _make_state(plan)

        with patch("app.agents.resource_validator._is_ssrf_target", return_value=False):
            result = await validate_resources(state)

        assert result["learning_plan"].phases[0].resources[0].url is None
        assert result["learning_plan"].phases[1].resources[0].url is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_concurrency_respects_semaphore(self):
        """Verify no more than _MAX_CONCURRENT requests run simultaneously."""
        max_concurrent_seen = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def _tracking_handler(request: httpx.Request) -> httpx.Response:
            nonlocal max_concurrent_seen, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent_seen = max(max_concurrent_seen, current_concurrent)
            await asyncio.sleep(0.01)
            async with lock:
                current_concurrent -= 1
            return httpx.Response(200, headers={"content-type": "application/json"})

        for i in range(20):
            respx.head(f"https://example.com/{i}").mock(side_effect=_tracking_handler)

        resources = [
            Resource(type="article", title=f"R{i}", url=f"https://example.com/{i}")
            for i in range(20)
        ]
        plan = _make_plan(resources)
        state = _make_state(plan)

        with patch("app.agents.resource_validator._is_ssrf_target", return_value=False):
            await validate_resources(state)

        assert max_concurrent_seen <= 10

    @pytest.mark.asyncio
    async def test_pipeline_never_fails(self):
        """Even if everything goes wrong, the node returns the plan unchanged."""
        plan = _make_plan(
            [
                Resource(type="article", title="Test", url="https://example.com/test"),
            ]
        )
        state = _make_state(plan)

        with patch(
            "app.agents.resource_validator._check_with_cache",
            side_effect=RuntimeError("catastrophic failure"),
        ):
            result = await validate_resources(state)

        # gather(return_exceptions=True) catches the error; URL defaults to valid
        assert result["learning_plan"].phases[0].resources[0].url == "https://example.com/test"
