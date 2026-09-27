"""Tests for docs and ADR loading (spec F1 step 6)."""

from core.ingest.docs import load_docs


def test_loads_readme(fixture_repo):
    docs = load_docs(fixture_repo)
    readmes = [d for d in docs if d.path == "README.md"]
    assert len(readmes) == 1
    assert readmes[0].type == "doc"


def test_loads_adr_with_adr_type(fixture_repo):
    docs = load_docs(fixture_repo)
    adrs = [d for d in docs if d.type == "adr"]
    assert any("0001-use-sqlite" in d.path for d in adrs)
    assert any("SQLite" in d.text for d in adrs)


def test_no_duplicates(fixture_repo):
    docs = load_docs(fixture_repo)
    paths = [d.path for d in docs]
    assert len(paths) == len(set(paths))
