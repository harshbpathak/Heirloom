"""Tests for BM25 search and Ask Heirloom (F8): ranking, no-answer, citations."""

import json

from core.db import session_for
from core.llm.provider import LLMProvider, NullProvider
from core.search.index import DecisionIndex
from core.services.ask import ask, route_question


def test_routing_rules():
    assert route_question("Who knows the billing module?") == "who"
    assert route_question("What breaks if I change utils.py?") == "impact"
    assert route_question("Why do we use Redis?") == "decisions"


def test_bm25_ranks_relevant_decision_first(ingested_repo):
    with session_for(ingested_repo) as session:
        index = DecisionIndex(session, ingested_repo)
        hits = index.search("redis session storage")
        assert hits
        from core.models.db_models import Decision

        top = session.get(Decision, hits[0].decision_id)
        assert "redis" in top.title.lower()


def test_ask_decisions_without_llm_is_labeled(ingested_repo):
    with session_for(ingested_repo) as session:
        answer = ask(session, ingested_repo, "Why do we use Redis for sessions?", NullProvider())
    assert answer.route == "decisions"
    assert "LLM not configured" in answer.answer
    assert answer.citations


def test_ask_no_answer_path(ingested_repo):
    with session_for(ingested_repo) as session:
        answer = ask(session, ingested_repo, "quantum blockchain paradigm", NullProvider())
    assert "no recorded reasoning" in answer.answer


def test_ask_who_route(ingested_repo):
    with session_for(ingested_repo) as session:
        answer = ask(session, ingested_repo, "Who knows src/legacy.py?", NullProvider())
    assert answer.route == "who"
    assert "Bob Singh" in answer.answer


def test_ask_impact_route(ingested_repo):
    with session_for(ingested_repo) as session:
        answer = ask(
            session, ingested_repo, "What breaks if I change src/utils.py?", NullProvider()
        )
    assert answer.route == "impact"
    assert "src/app.py" in answer.answer


class CitingProvider(LLMProvider):
    """Mock LLM that answers with a fabricated citation plus a valid one."""

    name = "mock"

    def __init__(self, citations):
        self._citations = citations

    def complete_text(self, prompt: str) -> str:
        return json.dumps(
            {"answer": "Redis keeps sessions across restarts [1].", "citations": self._citations}
        )


def test_citation_enforcement_drops_invalid_ids(ingested_repo):
    with session_for(ingested_repo) as session:
        valid_ids = [h.decision_id for h in DecisionIndex(session, ingested_repo).search("redis")]
        provider = CitingProvider([str(valid_ids[0]), "99999"])
        answer = ask(session, ingested_repo, "Why do we use Redis?", provider)
    assert str(valid_ids[0]) in answer.citations
    assert "99999" not in answer.citations


def test_uncited_llm_claims_are_rejected(ingested_repo):
    with session_for(ingested_repo) as session:
        provider = CitingProvider(["99999"])  # only an invalid citation survives -> none
        # Different question text so the LLM cache from the previous test is not hit.
        answer = ask(session, ingested_repo, "Why was Redis chosen for storage?", provider)
    assert "no recorded reasoning" in answer.answer
