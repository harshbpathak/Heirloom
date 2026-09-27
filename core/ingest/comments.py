"""Intent-comment extraction (spec F1 step 5).

Finds comments that carry intent: NOTE, WHY, HACK, FIXME, TODO, XXX,
IMPORTANT, DO NOT, because, workaround, intentionally.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

INTENT_PATTERN = re.compile(
    r"\b(NOTE|WHY|HACK|FIXME|TODO|XXX|IMPORTANT|DO NOT|because|workaround|intentionally)\b",
    re.IGNORECASE,
)

# Markers that only count when written in upper case (avoid matching the word
# "note" in prose while still catching NOTE: tags).
UPPER_ONLY = {"NOTE", "WHY", "XXX", "IMPORTANT"}

# DO NOT add new markers here without updating the spec (F1 §5) and tests.
WARNING_MARKERS = ("DO NOT", "HACK", "FIXME", "XXX", "WARNING")

COMMENT_PREFIXES = {
    "python": ("#",),
    "javascript": ("//", "/*", "*"),
    "typescript": ("//", "/*", "*"),
    "vue": ("//", "/*", "*", "<!--"),
    "shell": ("#",),
    "yaml": ("#",),
    "toml": ("#",),
}


@dataclass
class IntentComment:
    """One intent-carrying comment found in a source file."""

    path: str
    line: int
    text: str

    @property
    def is_warning(self) -> bool:
        """True for markers that should surface as Why Card warnings."""
        upper = self.text.upper()
        return any(marker in upper for marker in WARNING_MARKERS)


def _has_intent(comment_text: str) -> bool:
    """Check whether a comment's text carries intent per the spec's word list."""
    for match in INTENT_PATTERN.finditer(comment_text):
        word = match.group(1)
        if word.upper() in UPPER_ONLY and word != word.upper():
            continue
        return True
    return False


def extract_intent_comments(
    repo_path: Path, rel_path: str, language: str | None
) -> list[IntentComment]:
    """Extract intent comments from one source file."""
    prefixes = COMMENT_PREFIXES.get(language or "", None)
    if prefixes is None:
        return []
    try:
        text = (repo_path / rel_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    results: list[IntentComment] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        comment_text = _comment_part(stripped, prefixes)
        if comment_text and _has_intent(comment_text):
            results.append(
                IntentComment(path=rel_path, line=lineno, text=comment_text.strip()[:500])
            )
    return results


def _comment_part(stripped_line: str, prefixes: tuple[str, ...]) -> str | None:
    """Return the comment portion of a line, or None when it has no comment."""
    for prefix in prefixes:
        if stripped_line.startswith(prefix):
            return stripped_line[len(prefix) :]
    # Trailing comments: look for the prefix mid-line (skip strings crudely —
    # good enough for intent mining, false negatives are acceptable).
    for prefix in ("#", "//"):
        if prefix in prefixes:
            idx = stripped_line.find(prefix, 1)
            if idx > 0 and not _inside_quotes(stripped_line, idx):
                return stripped_line[idx + len(prefix) :]
    return None


def _inside_quotes(line: str, idx: int) -> bool:
    """Heuristic: is position ``idx`` inside an odd number of quotes?"""
    before = line[:idx]
    return before.count('"') % 2 == 1 or before.count("'") % 2 == 1
