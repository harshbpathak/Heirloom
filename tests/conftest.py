"""Shared pytest fixtures: a fixture repo built once and ingested once."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.fixtures.make_repo import make_fixture_repo


@pytest.fixture(scope="session")
def fixture_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A deterministic git repo with known authors, imports and comments."""
    return make_fixture_repo(tmp_path_factory.mktemp("fixture") / "proj")


@pytest.fixture(scope="session", autouse=True)
def heirloom_home(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Isolated HEIRLOOM_HOME so tests never touch the user's real data."""
    home = tmp_path_factory.mktemp("heirloom_home")
    os.environ["HEIRLOOM_HOME"] = str(home)
    os.environ.pop("HEIRLOOM_DEMO", None)
    os.environ.pop("GITHUB_TOKEN", None)
    os.environ.pop("WATSONX_API_KEY", None)
    os.environ.pop("LLM_BASE_URL", None)
    return home


@pytest.fixture(scope="session")
def ingested_repo(fixture_repo: Path, heirloom_home: Path) -> str:
    """The fixture repo ingested end-to-end (no LLM); returns the repo id."""
    from core.ingest.pipeline import ingest_repo

    return ingest_repo(str(fixture_repo))
