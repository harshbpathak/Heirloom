"""Tests for the LLM provider layer: JSON parsing, provider selection, cache."""

import pytest

from core.config import get_settings
from core.errors import LLMError
from core.llm.provider import (
    LLMProvider,
    NullProvider,
    cache_key,
    cached_complete_json,
    get_provider,
    parse_json_response,
)


def test_parse_plain_json():
    assert parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_fenced_json():
    assert parse_json_response('Here you go:\n```json\n{"a": 1}\n```\nDone.') == {"a": 1}


def test_parse_json_with_surrounding_prose():
    assert parse_json_response('The answer is {"a": 1} as requested') == {"a": 1}


def test_parse_invalid_json_raises():
    with pytest.raises(LLMError):
        parse_json_response("no json here")


def test_parse_non_object_raises():
    with pytest.raises(LLMError):
        parse_json_response("[1, 2, 3]")


def test_provider_selection_defaults_to_null(heirloom_home):
    provider = get_provider(get_settings())
    assert isinstance(provider, NullProvider)
    assert not provider.available


def test_cache_key_is_stable():
    assert cache_key("p", "x") == cache_key("p", "x")
    assert cache_key("p", "x") != cache_key("p", "y")


class CountingProvider(LLMProvider):
    name = "counting"

    def __init__(self):
        self.calls = 0

    def complete_text(self, prompt: str) -> str:
        self.calls += 1
        return '{"ok": true}'


def test_cached_complete_json_hits_cache(ingested_repo):
    from core.db import session_for

    provider = CountingProvider()
    with session_for(ingested_repo) as session:
        first = cached_complete_json(provider, session, "prompt", "payload-cache-test")
        second = cached_complete_json(provider, session, "prompt", "payload-cache-test")
    assert first == second == {"ok": True}
    assert provider.calls == 1
