"""Tests for impact-set ranking (spec F3 step 4)."""

from core.analysis.impact import compute_impact


def test_direct_importer_ranks_above_two_hop():
    importers = {"target.py": {"direct.py"}, "direct.py": {"indirect.py"}}
    entries = compute_impact("target.py", importers, {}, {}, limit=10)
    paths = [e.path for e in entries]
    assert paths == ["direct.py", "indirect.py"]
    assert entries[0].score > entries[1].score
    assert "imports this file directly" in entries[0].reason


def test_coupling_contributes():
    coupling = {("other.py", "target.py"): (7, 0.9)}
    entries = compute_impact("target.py", {}, coupling, {"other.py": 9, "target.py": 8}, limit=10)
    assert entries[0].path == "other.py"
    assert "changed together in 7" in entries[0].reason


def test_combined_score_formula():
    importers = {"target.py": {"both.py"}}
    coupling = {("both.py", "target.py"): (5, 0.5)}
    entries = compute_impact("target.py", importers, coupling, {}, limit=10)
    # 0.6 * 1.0 + 0.4 * 0.5 = 0.8
    assert abs(entries[0].score - 0.8) < 1e-6


def test_limit_and_cap():
    importers = {"t.py": {f"f{i}.py" for i in range(30)}}
    entries = compute_impact("t.py", importers, {}, {}, limit=50)
    assert len(entries) == 20  # hard cap from the spec
