"""MCP tool tests: happy path, bad path, response size limit (spec §6)."""

import json

import pytest

from mcp_server import server


@pytest.fixture(autouse=True)
def _needs_repo(ingested_repo):
    return ingested_repo


def _call(tool_fn, **kwargs):
    """Call the undecorated tool function."""
    return tool_fn.fn(**kwargs) if hasattr(tool_fn, "fn") else tool_fn(**kwargs)


def test_ask_why_happy_path(ingested_repo):
    result = _call(server.ask_why, path="src/auth/session.py", repo_id=ingested_repo)
    assert result["path"] == "src/auth/session.py"
    assert "decisions" in result and "warnings" in result
    assert any("DO NOT" in w["text"] for w in result["warnings"])


def test_ask_why_bad_path_returns_clear_error(ingested_repo):
    result = _call(server.ask_why, path="missing.py", repo_id=ingested_repo)
    assert result["error"]["code"] == "file_not_found"
    assert "missing.py" in result["error"]["message"]


def test_who_knows(ingested_repo):
    result = _call(server.who_knows, path="src/legacy.py", repo_id=ingested_repo)
    assert result["bus_factor"] == 1
    assert result["at_risk"] is True
    assert result["holders"][0]["name"] == "Bob Singh"


def test_impact_if_changed(ingested_repo):
    result = _call(server.impact_if_changed, path="src/utils.py", repo_id=ingested_repo)
    assert any(i["path"] == "src/app.py" for i in result["impact"])


def test_onboarding_trail(ingested_repo):
    result = _call(server.onboarding_trail, repo_id=ingested_repo)
    assert result["steps"]
    assert all("reason" in s for s in result["steps"])


def test_search_decisions(ingested_repo):
    result = _call(server.search_decisions, query="redis", repo_id=ingested_repo)
    assert result["decisions"]


def test_record_decision_roundtrip(ingested_repo, fixture_repo):
    result = _call(
        server.record_decision,
        title="Pin the date library",
        files=["web/helpers.ts"],
        reasoning="Because minor upgrades broke ISO formatting twice.",
        repo_id=ingested_repo,
    )
    assert result["id"]
    assert (fixture_repo / result["record_path"]).is_file()


def test_record_decision_validation_error(ingested_repo):
    result = _call(
        server.record_decision, title="  ", files=[], reasoning="x", repo_id=ingested_repo
    )
    assert result["error"]["code"] == "validation_failed"


def test_repo_risk_report(ingested_repo):
    result = _call(server.repo_risk_report, repo_id=ingested_repo)
    assert any(f["path"] == "src/legacy.py" for f in result["at_risk_files"])


def test_response_size_limit():
    payload = {"items": [{"text": "x" * 400} for _ in range(100)]}
    trimmed = server._truncate(payload, ["items"])
    assert len(json.dumps(trimmed)) <= server.MAX_RESPONSE_CHARS + 200
    assert "truncated" in trimmed
    assert "items cut" in trimmed["truncated"]


def test_record_decision_stores_skill_hash(ingested_repo, fixture_repo):
    from core.decisions.capture import parse_decision_record

    result = _call(
        server.record_decision,
        title="Cache compiled templates",
        files=["src/app.py"],
        reasoning="Because template compilation dominated request time.",
        skill_hash="abc123def",
        repo_id=ingested_repo,
    )
    record = parse_decision_record((fixture_repo / result["record_path"]).read_text("utf-8"))
    assert record.skill_hash == "abc123def"


def test_default_repo_honors_env(ingested_repo, monkeypatch):
    monkeypatch.setenv("HEIRLOOM_REPO", ingested_repo)
    assert server._default_repo() == ingested_repo
    monkeypatch.setenv("HEIRLOOM_REPO", "some-other-repo")
    result = _call(server.who_knows, path="src/legacy.py")
    assert result["error"]["code"] == "repo_not_found"
