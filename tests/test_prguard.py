"""PR guard tests (spec F10): diff parsing, DO NOT proximity, strict mode, comment snapshot."""

import re
from pathlib import Path

import pytest

from core.models.schemas import HolderSchema
from core.prguard import (
    COMMENT_MARKER,
    build_report,
    parse_changed_lines,
    render_comment,
    reviewer_is_holder,
)

SNAPSHOT = Path(__file__).parent / "snapshots" / "pr_comment.md"

DIFF = """diff --git a/src/auth/session.py b/src/auth/session.py
--- a/src/auth/session.py
+++ b/src/auth/session.py
@@ -5,0 +6,2 @@ def get():
+    x = 1
+    y = 2
diff --git a/old.py b/old.py
--- a/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-gone
"""


def test_parse_changed_lines():
    changed = parse_changed_lines(DIFF)
    assert changed == {"src/auth/session.py": [6, 7]}  # deleted file is skipped


def test_parse_deletion_only_hunk_records_neighbor_line():
    diff = "+++ b/a.py\n@@ -10,2 +9,0 @@\n"
    assert parse_changed_lines(diff) == {"a.py": [9]}


def test_reviewer_matching():
    holders = [HolderSchema(name="Alice Chen", ownership=0.9)]
    assert reviewer_is_holder(["alicechen"], holders)
    assert reviewer_is_holder(["achen-dev"], holders)
    assert not reviewer_is_holder(["bob"], holders)


@pytest.fixture()
def guard_repo(tmp_path, monkeypatch):
    """An isolated ingest so other tests' recorded decisions don't leak in."""
    from core.db import dispose_engines
    from core.ingest.pipeline import ingest_repo
    from tests.fixtures.make_repo import make_fixture_repo

    monkeypatch.setenv("HEIRLOOM_HOME", str(tmp_path / "home"))
    repo = make_fixture_repo(tmp_path / "guardproj")
    repo_id = ingest_repo(str(repo))
    yield repo_id, repo
    dispose_engines()


def _report(guard_repo, changed, **kwargs):
    from core.db import session_for

    repo_id, repo = guard_repo
    with session_for(repo_id) as session:
        return build_report(session, repo_id, repo, changed, **kwargs)


def test_do_not_warning_only_near_changed_lines(guard_repo):
    near = _report(guard_repo, {"src/auth/session.py": [5]})
    far = _report(guard_repo, {"src/auth/session.py": [40]})
    assert near.files[0].do_not_warnings
    assert not far.files[0].do_not_warnings


def test_impact_excludes_files_already_in_pr(guard_repo):
    report = _report(guard_repo, {"src/utils.py": [3], "src/app.py": [1]})
    utils = next(f for f in report.files if f.path == "src/utils.py")
    assert "src/app.py" not in [p for p, _ in utils.impact_outside_pr]


def test_strict_mode_fails_without_holder_reviewer(guard_repo):
    report = _report(guard_repo, {"src/legacy.py": [3]}, reviewers=["someone"], strict=True)
    assert report.strict_failures and "src/legacy.py" in report.strict_failures[0]
    ok = _report(guard_repo, {"src/legacy.py": [3]}, reviewers=["bsingh"], strict=True)
    assert not ok.strict_failures


def test_comment_body_snapshot(guard_repo):
    report = _report(
        guard_repo,
        {"src/auth/session.py": [5], "src/utils.py": [3], "brand_new.py": [1]},
    )
    body = render_comment(report)
    assert body.startswith(COMMENT_MARKER)
    normalized = re.sub(r"\b[0-9a-f]{40}\b", "<sha>", body)
    if not SNAPSHOT.exists():  # first run writes the snapshot; commit it
        SNAPSHOT.write_text(normalized, encoding="utf-8")
    assert normalized == SNAPSHOT.read_text(encoding="utf-8")
