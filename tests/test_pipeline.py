"""End-to-end ingestion tests against the fixture repo (F1, F3, F4)."""

from sqlalchemy import select

from core.db import session_for
from core.models.db_models import Commit, Decision, Evidence, File, Import


def test_ingest_creates_files(ingested_repo):
    with session_for(ingested_repo) as session:
        paths = set(session.scalars(select(File.path).where(File.repo_id == ingested_repo)))
    assert "src/app.py" in paths
    assert "web/index.ts" in paths
    assert "docs/adr/0001-use-sqlite.md" in paths


def test_ingest_stores_commits(ingested_repo):
    with session_for(ingested_repo) as session:
        commits = session.scalars(select(Commit).where(Commit.repo_id == ingested_repo)).all()
    assert len(commits) == 10


def test_import_edges_resolved(ingested_repo):
    with session_for(ingested_repo) as session:
        files = {f.id: f.path for f in session.scalars(select(File))}
        edges = {
            (files[i.src_file_id], files[i.dst_file_id]) for i in session.scalars(select(Import))
        }
    assert ("src/app.py", "src/utils.py") in edges
    assert ("web/index.ts", "web/helpers.ts") in edges


def test_fan_in_computed(ingested_repo):
    with session_for(ingested_repo) as session:
        utils = session.scalar(select(File).where(File.path == "src/utils.py"))
        assert utils.fan_in >= 1


def test_entry_point_detected(ingested_repo):
    with session_for(ingested_repo) as session:
        app = session.scalar(select(File).where(File.path == "src/app.py"))
        assert app.is_entry_point


def test_bus_factor_and_at_risk(ingested_repo):
    with session_for(ingested_repo) as session:
        legacy = session.scalar(select(File).where(File.path == "src/legacy.py"))
        utils = session.scalar(select(File).where(File.path == "src/utils.py"))
    # Bob alone wrote legacy.py and has been inactive for ~2 years.
    assert legacy.bus_factor == 1
    assert legacy.at_risk
    # Alice actively maintains utils.py.
    assert utils.bus_factor is not None and not utils.at_risk


def test_decisions_extracted_with_evidence(ingested_repo):
    with session_for(ingested_repo) as session:
        decisions = session.scalars(select(Decision).where(Decision.repo_id == ingested_repo)).all()
        assert decisions, "heuristic extractor should find decisions without an LLM"
        assert any("redis" in d.title.lower() for d in decisions)
        # Every decision links to at least one evidence item (acceptance criterion).
        from core.models.db_models import DecisionEvidence

        for d in decisions:
            links = session.scalars(
                select(DecisionEvidence).where(DecisionEvidence.decision_id == d.id)
            ).all()
            assert links, f"decision {d.id} has no evidence"


def test_adr_becomes_high_confidence_decision(ingested_repo):
    with session_for(ingested_repo) as session:
        decisions = session.scalars(select(Decision).where(Decision.confidence == "high")).all()
    assert any("sqlite" in d.title.lower() for d in decisions)


def test_reingest_is_incremental_and_idempotent(ingested_repo, fixture_repo):
    from core.ingest.pipeline import ingest_repo

    with session_for(ingested_repo) as session:
        before_commits = len(session.scalars(select(Commit)).all())
        before_decisions = len(session.scalars(select(Decision)).all())
        before_evidence = len(session.scalars(select(Evidence)).all())

    ingest_repo(str(fixture_repo))  # no new commits

    with session_for(ingested_repo) as session:
        assert len(session.scalars(select(Commit)).all()) == before_commits
        assert len(session.scalars(select(Decision)).all()) == before_decisions
        assert len(session.scalars(select(Evidence)).all()) == before_evidence


def test_active_owner_file_is_not_at_risk(ingested_repo):
    # Alice owns session.py and committed recently elsewhere in the repo.
    with session_for(ingested_repo) as session:
        session_file = session.scalar(select(File).where(File.path == "src/auth/session.py"))
    assert session_file.bus_factor == 1
    assert not session_file.at_risk


def test_comment_decisions_have_unknown_date_not_invented(ingested_repo):
    from core.models.db_models import DecisionEvidence

    with session_for(ingested_repo) as session:
        rows = session.execute(
            select(Decision, Evidence.type)
            .join(DecisionEvidence, DecisionEvidence.decision_id == Decision.id)
            .join(Evidence, Evidence.id == DecisionEvidence.evidence_id)
            .where(Evidence.type == "code_comment")
        ).all()
    assert rows
    assert all(decision.created_at is None for decision, _ in rows)


def test_canonical_author_name_in_holders(ingested_repo):
    from core.services.queries import holders_for_file

    with session_for(ingested_repo) as session:
        utils = session.scalar(select(File).where(File.path == "src/utils.py"))
        names = [h.name for h in holders_for_file(session, utils)]
    assert "Alice Chen" in names
    assert "Alice C" not in names
