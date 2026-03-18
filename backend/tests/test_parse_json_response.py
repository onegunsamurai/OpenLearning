"""Tests for parse_json_response from app.services.ai."""

from __future__ import annotations

import json

import pytest

from app.services.ai import parse_json_response


class TestParseJsonResponse:
    def test_plain_json(self):
        result = parse_json_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_with_json_code_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_json_with_bare_code_fence(self):
        text = '```\n{"key": "value"}\n```'
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_whitespace_trimmed(self):
        text = '  \n  {"key": "value"}  \n  '
        result = parse_json_response(text)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_response("not json at all")

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_response("")

    def test_returns_dict(self):
        result = parse_json_response('{"a": 1, "b": [2, 3]}')
        assert isinstance(result, dict)
        assert result["a"] == 1
        assert result["b"] == [2, 3]
