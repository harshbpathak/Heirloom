"""Tests for decision extraction: candidate filter, heuristics, LLM validation, dedupe (F2)."""

import json
from datetime import datetime

import pytest

from core.decisions.dedupe import merge_decisions
from core.decisions.extraction import (
    EvidenceCandidate,
    heuristic_extract,
    is_candidate,
    llm_extract,
)
from core.errors import LLMError
from core.llm.provider import LLMProvider


def _commit(text: str, ref: str = "abc123", files=None) -> EvidenceCandidate:
    return EvidenceCandidate(
        type="commit", ref=ref, text=text, files=files or ["a.py"], date=datetime(2026, 1, 1)
    )


def test_short_boring_commit_is_not_candidate():
    assert not is_candidate(_commit("fix typo"))


def test_long_commit_is_candidate():
    assert is_candidate(_commit("x" * 61))


def test_keyword_commit_is_candidate():
    assert is_candidate(_commit("revert bad change"))
    assert is_candidate(_commit("use redis because of restarts"))


def test_comments_and_adrs_always_candidates():
    assert is_candidate(EvidenceCandidate(type="code_comment", ref="a.py:1", text="HACK"))
    assert is_candidate(EvidenceCandidate(type="adr", ref="docs/adr/1.md", text="x"))


def test_pr_needs_long_body():
    short = EvidenceCandidate(type="pull_request", ref="1", text="Title\nshort body")
    long = EvidenceCandidate(type="pull_request", ref="2", text="Title\n" + "b" * 120)
    assert not is_candidate(short)
    assert is_candidate(long)


def test_heuristic_title_and_reasoning():
    draft = heuristic_extract(
        _commit(
            "Use Redis for sessions because they must survive restarts\n\n"
            "We chose Redis instead of memory. This works so that deploys are safe."
        )
    )
    assert draft.title.startswith("Use Redis for sessions")
    assert len(draft.title) <= 80
    assert "instead of" in draft.reasoning and draft.title not in draft.reasoning
    assert draft.confidence == "low"


def test_heuristic_adr_confidence_high():
    adr = EvidenceCandidate(
        type="adr", ref="docs/adr/1.md", text="Use SQLite\n\nWe use it because it is zero-setup."
    )
    assert heuristic_extract(adr).confidence == "high"


class FakeProvider(LLMProvider):
    """Provider returning canned JSON for validation tests."""

    name = "fake"

    def __init__(self, response):
        self._response = response

    def complete_text(self, prompt: str) -> str:
        return json.dumps(self._response)


class FakeSession:
    """Minimal stand-in for the SQLAlchemy session used by the LLM cache."""

    def get(self, *_args):
        return None

    def add(self, *_args):
        pass


def test_llm_extract_valid_output():
    provider = FakeProvider(
        {
            "decisions": [
                {
                    "title": "Use Redis",
                    "summary": "s",
                    "reasoning": "r",
                    "alternatives": None,
                    "files": ["a.py"],
                    "evidence_refs": ["commit:abc123"],
                }
            ]
        }
    )
    candidates = [_commit("Use Redis because restarts happen and sessions must survive them ok")]
    decisions, dropped = llm_extract(provider, FakeSession(), candidates)
    assert len(decisions) == 1
    assert decisions[0].confidence == "medium"
    assert dropped == []


def test_llm_extract_rejects_bad_json_falls_back_to_heuristic():
    class BadProvider(LLMProvider):
        name = "bad"

        def complete_text(self, prompt: str) -> str:
            return "not json at all {{{"

    candidates = [_commit("Use Redis because restarts happen and sessions must survive them ok")]
    decisions, _ = llm_extract(BadProvider(), FakeSession(), candidates)
    # Falls back to the heuristic path, so we still get a (low-confidence) decision.
    assert len(decisions) == 1
    assert decisions[0].confidence == "low"


def test_llm_extract_drops_decision_with_unknown_evidence():
    provider = FakeProvider(
        {
            "decisions": [
                {
                    "title": "Ghost",
                    "summary": "",
                    "reasoning": "",
                    "alternatives": None,
                    "files": [],
                    "evidence_refs": ["commit:doesnotexist"],
                }
            ]
        }
    )
    candidates = [_commit("Use Redis because restarts happen and sessions must survive them ok")]
    decisions, dropped = llm_extract(provider, FakeSession(), candidates)
    assert decisions == []
    assert dropped == ["Ghost"]


def test_llm_extract_rejects_overlong_title():
    provider = FakeProvider(
        {
            "decisions": [
                {
                    "title": "x" * 200,
                    "summary": "",
                    "reasoning": "",
                    "alternatives": None,
                    "files": [],
                    "evidence_refs": ["commit:abc123"],
                }
            ]
        }
    )
    candidates = [_commit("Use Redis because restarts happen and sessions must survive them ok")]
    # Pydantic rejects the batch -> heuristic fallback produces a valid short title.
    decisions, _ = llm_extract(provider, FakeSession(), candidates)
    assert all(len(d.title) <= 80 for d in decisions)


def test_dedupe_merges_similar_titles_same_files():
    a = heuristic_extract(_commit("Use Redis for session storage because restarts", ref="c1"))
    b = heuristic_extract(_commit("Use Redis for session storage because restart", ref="c2"))
    merged = merge_decisions([a, b])
    assert len(merged) == 1
    assert set(merged[0].evidence_refs) == {"commit:c1", "commit:c2"}


def test_dedupe_keeps_different_files_apart():
    a = heuristic_extract(
        _commit("Use Redis for session storage because restarts", ref="c1", files=["a.py"])
    )
    b = heuristic_extract(
        _commit("Use Redis for session storage because restarts", ref="c2", files=["b.py"])
    )
    assert len(merge_decisions([a, b])) == 2


def test_null_provider_raises():
    from core.llm.provider import NullProvider

    with pytest.raises(LLMError):
        NullProvider().complete_text("hi")


def test_adr_markdown_is_cleaned_for_title_and_reasoning():
    adr = EvidenceCandidate(
        type="adr",
        ref="docs/adr/0001.md",
        text="# 1. Use SQLite for local storage\n\n## Status\nAccepted\n\n## Decision\n"
        "Use SQLite because it requires no server.\n",
    )
    draft = heuristic_extract(adr)
    assert draft.title == "Use SQLite for local storage"
    assert "#" not in draft.reasoning
    assert draft.reasoning == "Use SQLite because it requires no server."


def test_reasoning_does_not_repeat_title_when_body_has_reasons():
    draft = heuristic_extract(
        _commit(
            "Use Redis for sessions because restarts\n\n"
            "We picked Redis instead of memcached. It is fine."
        )
    )
    assert draft.reasoning == "We picked Redis instead of memcached."
