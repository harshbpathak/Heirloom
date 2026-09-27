"""Tests for Why Card assembly and the agent-context budget (F5, §10.3)."""

from core.db import session_for
from core.llm.provider import NullProvider
from core.services.whycard import agent_context, build_why_card, why_card_markdown


def _card(ingested_repo, fixture_repo, path="src/auth/session.py"):
    with session_for(ingested_repo) as session:
        return build_why_card(
            session, ingested_repo, path, repo_path=fixture_repo, provider=NullProvider()
        )


def test_summary_falls_back_to_header_comment(ingested_repo, fixture_repo):
    card = _card(ingested_repo, fixture_repo)
    assert card.summary_source == "comment"
    assert "Session storage" in card.summary


def test_summary_honest_when_nothing_known(ingested_repo, fixture_repo):
    card = _card(ingested_repo, fixture_repo, path="src/__init__.py")
    assert card.summary_source == "none"
    assert "No summary available" in card.summary


def test_warnings_present_with_line_numbers(ingested_repo, fixture_repo):
    card = _card(ingested_repo, fixture_repo)
    assert any(w.line == 2 and "DO NOT" in w.text for w in card.warnings)


def test_activity_timeline(ingested_repo, fixture_repo):
    card = _card(ingested_repo, fixture_repo, path="src/utils.py")
    assert card.activity
    assert all(p.commits > 0 for p in card.activity)


def test_agent_context_under_token_budget(ingested_repo, fixture_repo):
    card = _card(ingested_repo, fixture_repo)
    ctx = agent_context(card)
    assert len(ctx.model_dump_json()) < 6000  # ~1500 tokens
    assert ctx.path == card.path
    assert ctx.ask  # top holder name


def test_markdown_render_has_all_sections(ingested_repo, fixture_repo):
    md = why_card_markdown(_card(ingested_repo, fixture_repo))
    for heading in ("Why it is like this", "Knowledge holders", "Impact if changed", "Warnings"):
        assert heading in md
