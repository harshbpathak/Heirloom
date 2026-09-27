"""Tests for commit-log parsing (spec F1 step 3)."""

from core.ingest.gitlog import _normalize_numstat_path, head_commit, read_git_log


def test_reads_all_commits(fixture_repo):
    entries = read_git_log(fixture_repo)
    assert len(entries) == 10  # scripted in make_repo.py


def test_commit_fields(fixture_repo):
    entries = read_git_log(fixture_repo)
    newest = entries[0]
    assert newest.author_name == "Alice Chen"
    assert newest.author_email == "alice@example.com"
    assert "format()" in newest.message
    assert any(path == "src/utils.py" for path, _, _ in newest.files)


def test_numstat_counts_positive(fixture_repo):
    entries = read_git_log(fixture_repo)
    oldest = entries[-1]
    files = {p: (a, d) for p, a, d in oldest.files}
    assert "src/legacy.py" in files
    assert files["src/legacy.py"][0] > 0


def test_max_commits_limit(fixture_repo):
    assert len(read_git_log(fixture_repo, max_commits=3)) == 3


def test_after_commit_incremental(fixture_repo):
    entries = read_git_log(fixture_repo)
    third = entries[2].hash
    newer = read_git_log(fixture_repo, after_commit=third)
    assert [e.hash for e in newer] == [entries[0].hash, entries[1].hash]


def test_head_commit(fixture_repo):
    entries = read_git_log(fixture_repo)
    assert head_commit(fixture_repo) == entries[0].hash


def test_rename_path_normalization():
    assert _normalize_numstat_path("src/{old => new}/f.py") == "src/new/f.py"
    assert _normalize_numstat_path("old.py => new.py") == "new.py"
    assert _normalize_numstat_path("plain.py") == "plain.py"
