"""Loader for the versioned prompt files in ``core/llm/prompts/``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load a prompt by file stem (e.g. ``decision_extraction``)."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
