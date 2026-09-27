"""Tests for knowledge-base export."""

import json

from core.db import session_for
from core.export.exporter import export_json, export_markdown


def test_export_json_structure(ingested_repo):
    with session_for(ingested_repo) as session:
        data = json.loads(export_json(session, ingested_repo))
    assert data["repo"]["id"] == ingested_repo
    assert data["decisions"]
    assert data["files"]


def test_export_markdown_contains_decisions(ingested_repo):
    with session_for(ingested_repo) as session:
        md = export_markdown(session, ingested_repo)
    assert md.startswith("# Heirloom knowledge base")
    assert "## Decisions" in md
    assert "At-risk files" in md
    assert "src/legacy.py" in md
