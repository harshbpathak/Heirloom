"""Tests for onboarding trails (spec F7)."""

from core.db import session_for
from core.llm.provider import NullProvider
from core.trails.builder import build_trail


def test_general_trail_orders_dependencies_first(ingested_repo):
    with session_for(ingested_repo) as session:
        trail = build_trail(session, ingested_repo, provider=NullProvider())
    paths = [s.path for s in trail.steps]
    assert paths, "general trail must not be empty"
    # utils.py is imported by app.py, so it must come first when both appear.
    if "src/utils.py" in paths and "src/app.py" in paths:
        assert paths.index("src/utils.py") < paths.index("src/app.py")


def test_topic_trail_has_no_zero_relevance_files(ingested_repo):
    with session_for(ingested_repo) as session:
        trail = build_trail(session, ingested_repo, topic="redis session", provider=NullProvider())
    paths = [s.path for s in trail.steps]
    assert "src/auth/session.py" in paths
    assert "src/legacy.py" not in paths  # unrelated to the topic


def test_reading_time_minimum_one_minute(ingested_repo):
    with session_for(ingested_repo) as session:
        trail = build_trail(session, ingested_repo, provider=NullProvider())
    assert all(s.reading_minutes >= 1 for s in trail.steps)


def test_template_reasons_without_llm(ingested_repo):
    with session_for(ingested_repo) as session:
        trail = build_trail(session, ingested_repo, provider=NullProvider())
    assert all(s.reason.strip() for s in trail.steps)
    assert any("Imported by" in s.reason or "entry point" in s.reason for s in trail.steps)
