"""Tests for co-change coupling math (spec F3 step 3)."""

from core.analysis.coupling import compute_coupling


def test_basic_coupling_score():
    commits = [["a.py", "b.py"]] * 3 + [["a.py"]] * 6
    pairs = compute_coupling(commits)
    assert len(pairs) == 1
    pair = pairs[0]
    # co_changes=3, changes(a)=9, changes(b)=3 -> 3/min(9,3) = 1.0
    assert pair.co_changes == 3
    assert pair.score == 1.0


def test_below_min_co_changes_dropped():
    commits = [["a.py", "b.py"]] * 2
    assert compute_coupling(commits) == []


def test_below_min_score_dropped():
    # co=3 but both files change 20 times -> 3/20 = 0.15 < 0.3
    commits = [["a.py", "b.py"]] * 3 + [["a.py"], ["b.py"]] * 17
    assert compute_coupling(commits) == []


def test_bulk_commits_ignored():
    big = [f"f{i}.py" for i in range(40)]
    commits = [big] * 5
    assert compute_coupling(commits) == []


def test_duplicate_paths_in_one_commit_count_once():
    commits = [["a.py", "a.py", "b.py"]] * 3
    pairs = compute_coupling(commits)
    assert pairs[0].co_changes == 3
