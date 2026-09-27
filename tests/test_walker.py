"""Tests for file walking and skip rules (spec F1 step 2)."""

from pathlib import Path

from core.ingest.walker import detect_language, should_skip, walk_repo


def test_skips_node_modules():
    assert should_skip(Path("node_modules/react/index.js"), 100)


def test_skips_lockfiles():
    assert should_skip(Path("package-lock.json"), 100)
    assert should_skip(Path("poetry.lock"), 100)


def test_skips_binaries_and_large_files():
    assert should_skip(Path("logo.png"), 100)
    assert should_skip(Path("big.py"), 2_000_000)


def test_keeps_normal_source_files():
    assert not should_skip(Path("src/app.py"), 1000)
    assert not should_skip(Path("web/index.tsx"), 1000)


def test_detect_language():
    assert detect_language("a/b.py") == "python"
    assert detect_language("a/b.tsx") == "typescript"
    assert detect_language("a/b.vue") == "vue"
    assert detect_language("a/b.unknownext") is None


def test_walk_fixture_repo(fixture_repo):
    files = {f.path: f for f in walk_repo(fixture_repo)}
    assert "src/app.py" in files
    assert "web/index.ts" in files
    assert files["src/app.py"].language == "python"
    assert files["src/app.py"].loc > 0
    assert all(".git/" not in p for p in files)
