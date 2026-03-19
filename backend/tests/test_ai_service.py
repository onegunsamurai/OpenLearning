"""Tests for AI service contextvar and api_key threading."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.ai import (
    _current_api_key,
    api_key_scope,
    get_chat_model,
    reset_current_api_key,
    set_current_api_key,
)


class TestGetChatModelKeyThreading:
    def test_with_direct_param(self) -> None:
        with patch("app.services.ai.ChatAnthropic") as mock_cls:
            mock_cls.return_value = MagicMock()
            model = get_chat_model(api_key="sk-direct-key")
            assert model is not None
            mock_cls.assert_called_once()
            assert mock_cls.call_args[1]["anthropic_api_key"] == "sk-direct-key"

    def test_with_contextvar(self) -> None:
        token = set_current_api_key("sk-contextvar-key")
        try:
            with patch("app.services.ai.ChatAnthropic") as mock_cls:
                mock_cls.return_value = MagicMock()
                model = get_chat_model()
                assert model is not None
                mock_cls.assert_called_once()
                assert mock_cls.call_args[1]["anthropic_api_key"] == "sk-contextvar-key"
        finally:
            reset_current_api_key(token)

    def test_direct_param_overrides_contextvar(self) -> None:
        token = set_current_api_key("sk-contextvar-key")
        try:
            with patch("app.services.ai.ChatAnthropic") as mock_cls:
                mock_cls.return_value = MagicMock()
                model = get_chat_model(api_key="sk-direct-key")
                assert model is not None
                mock_cls.assert_called_once()
                assert mock_cls.call_args[1]["anthropic_api_key"] == "sk-direct-key"
        finally:
            reset_current_api_key(token)

    def test_fallback_to_settings(self) -> None:
        from app.config import Settings

        mock_settings = Settings(anthropic_api_key="sk-settings-key")
        with (
            patch("app.services.ai.get_settings", return_value=mock_settings),
            patch("app.services.ai.ChatAnthropic") as mock_cls,
        ):
            mock_cls.return_value = MagicMock()
            model = get_chat_model()
            assert model is not None
            assert mock_cls.call_args[1]["anthropic_api_key"] == "sk-settings-key"

    def test_no_key_raises_error(self) -> None:
        from app.config import Settings

        mock_settings = Settings(anthropic_api_key="")
        with (
            patch("app.services.ai.get_settings", return_value=mock_settings),
            pytest.raises(ValueError, match="No API key available"),
        ):
            get_chat_model()

    def test_contextvar_reset(self) -> None:
        token = set_current_api_key("sk-temp-key")
        assert _current_api_key.get() == "sk-temp-key"
        reset_current_api_key(token)
        assert _current_api_key.get() is None


class TestApiKeyScope:
    def test_sets_and_resets_key(self) -> None:
        assert _current_api_key.get() is None
        with api_key_scope("sk-scoped-key"):
            assert _current_api_key.get() == "sk-scoped-key"
        assert _current_api_key.get() is None

    def test_resets_on_exception(self) -> None:
        assert _current_api_key.get() is None
        with pytest.raises(RuntimeError), api_key_scope("sk-scoped-key"):
            raise RuntimeError("boom")
        assert _current_api_key.get() is None
