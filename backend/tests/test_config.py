"""Tests for app.config.Settings — focused on the YouTube enrichment additions
introduced in issue #177.

ACs covered: AC-7 (budget defaults), AC-11 (cap default), AC-15 (key never logged).
SRs covered: SR-01 (SecretStr), SR-03 (cap + budget), SR-04 (timeouts/concurrency),
SR-06 (cachetools available), SR-14 (.env.example placeholders).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr

from app.config import Settings, get_settings


class TestYoutubeSettingsDefaults:
    def test_youtube_api_key_default_is_empty_secretstr(self):
        """Empty key is the off-state / feature flag (AC-2, AC-15)."""
        s = Settings()
        assert isinstance(s.youtube_api_key, SecretStr)
        assert s.youtube_api_key.get_secret_value() == ""

    def test_max_video_lookups_per_plan_default(self):
        """AC-11 / SR-03: per-plan cap defaults to 12."""
        assert Settings().max_video_lookups_per_plan == 12

    def test_per_request_timeout_default(self):
        """SR-04: 10s per HTTP request."""
        assert Settings().youtube_per_request_timeout_seconds == 10.0

    def test_node_timeout_default(self):
        """SR-04: 30s for the whole enrich_videos node body."""
        assert Settings().youtube_node_timeout_seconds == 30.0

    def test_max_concurrent_searches_default(self):
        """SR-04: semaphore size for parallel search.list calls."""
        assert Settings().youtube_max_concurrent_searches == 5

    def test_daily_quota_budget_default(self):
        """SR-03 / AC-7: 80% of free-tier 10k = 8000 unit circuit-breaker budget."""
        assert Settings().youtube_daily_quota_budget == 8000


class TestYoutubeApiKeyMasked:
    """SR-01 / AC-15: API key must never appear in repr/str/log."""

    def test_repr_masks_secret(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "AIza-real-secret-value-do-not-leak")
        get_settings.cache_clear()
        s = Settings()
        assert "AIza-real-secret-value-do-not-leak" not in repr(s)
        assert "AIza-real-secret-value-do-not-leak" not in str(s)
        # The SecretStr field must round-trip the real value to the caller.
        assert s.youtube_api_key.get_secret_value() == "AIza-real-secret-value-do-not-leak"
        get_settings.cache_clear()


class TestCachetoolsAvailable:
    """SR-06: cachetools.TTLCache backs the bounded LRU+TTL caches in
    services/youtube.py."""

    def test_cachetools_importable(self):
        import cachetools

        assert hasattr(cachetools, "TTLCache")


class TestEnvExamplePlaceholders:
    """SR-14 / AC-15: .env.example documents the new settings with empty values
    and never carries a real Google API key."""

    @staticmethod
    def _read_env_example() -> str:
        env_example = Path(__file__).parent.parent / ".env.example"
        return env_example.read_text(encoding="utf-8")

    def test_youtube_api_key_documented(self):
        contents = self._read_env_example()
        assert "YOUTUBE_API_KEY=" in contents

    def test_max_video_lookups_documented(self):
        assert "MAX_VIDEO_LOOKUPS_PER_PLAN=12" in self._read_env_example()

    def test_per_request_timeout_documented(self):
        assert "YOUTUBE_PER_REQUEST_TIMEOUT_SECONDS=10" in self._read_env_example()

    def test_node_timeout_documented(self):
        assert "YOUTUBE_NODE_TIMEOUT_SECONDS=30" in self._read_env_example()

    def test_max_concurrent_searches_documented(self):
        assert "YOUTUBE_MAX_CONCURRENT_SEARCHES=5" in self._read_env_example()

    def test_daily_quota_budget_documented(self):
        assert "YOUTUBE_DAILY_QUOTA_BUDGET=8000" in self._read_env_example()

    def test_no_real_google_api_key_in_example(self):
        # Real Google API keys start with "AIza".
        assert "AIza" not in self._read_env_example()
