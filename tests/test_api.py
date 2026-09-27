"""API endpoint tests with FastAPI TestClient (spec §9.1)."""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture()
def client(ingested_repo):
    return TestClient(app)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["llm"] == "none"  # tests run with no keys
    assert body["demo"] is False


def test_list_repos(client, ingested_repo):
    body = client.get("/api/repos").json()
    ids = [r["id"] for r in body]
    assert ingested_repo in ids
    repo = next(r for r in body if r["id"] == ingested_repo)
    assert repo["stats"]["files"] > 0


def test_tree(client, ingested_repo):
    body = client.get(f"/api/repos/{ingested_repo}/tree").json()
    names = [c["name"] for c in body["children"]]
    assert "src" in names


def test_why_card(client, ingested_repo):
    body = client.get(
        f"/api/repos/{ingested_repo}/why", params={"path": "src/auth/session.py"}
    ).json()
    assert body["path"] == "src/auth/session.py"
    assert body["summary"]  # comment fallback, never invented
    assert body["summary_source"] in ("comment", "none")
    assert any("DO NOT" in w["text"] for w in body["warnings"])


def test_why_card_agent_format_under_budget(client, ingested_repo):
    resp = client.get(
        f"/api/repos/{ingested_repo}/why",
        params={"path": "src/auth/session.py", "format": "agent"},
    )
    assert resp.status_code == 200
    assert len(resp.text) < 6000  # ~1500 tokens


def test_why_unknown_path_404(client, ingested_repo):
    resp = client.get(f"/api/repos/{ingested_repo}/why", params={"path": "nope.py"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "file_not_found"


def test_unknown_repo_404(client):
    resp = client.get("/api/repos/doesnotexist/tree")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "repo_not_found"


def test_who(client, ingested_repo):
    body = client.get(f"/api/repos/{ingested_repo}/who", params={"path": "src/legacy.py"}).json()
    assert body["bus_factor"] == 1
    assert body["at_risk"] is True
    assert body["holders"][0]["name"] == "Bob Singh"
    assert "@" not in str(body["holders"])  # emails never leave the API


def test_impact(client, ingested_repo):
    body = client.get(f"/api/repos/{ingested_repo}/impact", params={"path": "src/utils.py"}).json()
    paths = [i["path"] for i in body["impact"]]
    assert "src/app.py" in paths
    assert all(i["reason"] for i in body["impact"])


def test_trail(client, ingested_repo):
    body = client.get(f"/api/repos/{ingested_repo}/trail").json()
    assert body["steps"]
    assert all(s["reason"] for s in body["steps"])


def test_trail_with_topic_excludes_irrelevant(client, ingested_repo):
    body = client.get(f"/api/repos/{ingested_repo}/trail", params={"topic": "session redis"}).json()
    paths = [s["path"] for s in body["steps"]]
    assert "src/auth/session.py" in paths


def test_ask(client, ingested_repo):
    body = client.post(f"/api/repos/{ingested_repo}/ask", json={"question": "Why Redis?"}).json()
    assert body["citations"]


def test_decisions_list_and_filter(client, ingested_repo):
    body = client.get(f"/api/repos/{ingested_repo}/decisions").json()
    assert body["total"] > 0
    filtered = client.get(f"/api/repos/{ingested_repo}/decisions", params={"q": "redis"}).json()
    assert 0 < filtered["total"] <= body["total"]


def test_create_decision_writes_record(client, ingested_repo, fixture_repo):
    resp = client.post(
        f"/api/repos/{ingested_repo}/decisions",
        json={
            "title": "Adopt strict typing in utils",
            "files": ["src/utils.py"],
            "reasoning": "Because runtime type errors kept reaching production.",
            "author": "Test User",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["record_path"] and body["record_path"].startswith(".heirloom/decisions/")
    assert (fixture_repo / body["record_path"]).is_file()


def test_risk(client, ingested_repo):
    body = client.get(f"/api/repos/{ingested_repo}/risk").json()
    assert any(f["path"] == "src/legacy.py" for f in body["at_risk_files"])
    assert body["bus_factor_1_loc_pct"] >= 0


def test_people(client, ingested_repo):
    body = client.get(f"/api/repos/{ingested_repo}/people").json()
    names = [p["name"] for p in body]
    assert "Alice Chen" in names or "Alice C" in names
    assert "@" not in str(body)


def test_ingest_rejected_in_demo_mode(client, monkeypatch):
    monkeypatch.setenv("HEIRLOOM_DEMO", "1")
    resp = client.post("/api/repos", json={"source": "https://github.com/x/y"})
    assert resp.status_code == 422
    monkeypatch.delenv("HEIRLOOM_DEMO")
