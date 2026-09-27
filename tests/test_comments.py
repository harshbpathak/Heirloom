"""Tests for intent-comment extraction (spec F1 step 5)."""

from core.ingest.comments import IntentComment, _has_intent, extract_intent_comments


def test_finds_do_not_comment(fixture_repo):
    comments = extract_intent_comments(fixture_repo, "src/auth/session.py", "python")
    texts = [c.text for c in comments]
    assert any("DO NOT" in t for t in texts)
    assert any("because" in t for t in texts)


def test_line_numbers_are_recorded(fixture_repo):
    comments = extract_intent_comments(fixture_repo, "src/auth/session.py", "python")
    do_not = next(c for c in comments if "DO NOT" in c.text)
    assert do_not.line == 2


def test_finds_hack_in_typescript(fixture_repo):
    comments = extract_intent_comments(fixture_repo, "web/helpers.ts", "typescript")
    assert any("HACK" in c.text for c in comments)


def test_warning_classification():
    assert IntentComment("f.py", 1, "DO NOT remove this").is_warning
    assert IntentComment("f.py", 1, "HACK: temporary").is_warning
    assert not IntentComment("f.py", 1, "we do this because of caching").is_warning


def test_intent_matcher_uppercase_only_words():
    assert _has_intent("NOTE: this matters")
    assert not _has_intent("please note the difference")  # lowercase 'note' is prose
    assert _has_intent("this is a workaround for the API")


def test_unsupported_language_returns_empty(fixture_repo):
    assert extract_intent_comments(fixture_repo, "README.md", "markdown") == []
