"""Loading of existing docs and ADRs (spec F1 step 6, F9 round-trip)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ADR_DIRS = ("docs/adr", "adr", "doc/architecture/decisions", ".heirloom/decisions")


@dataclass
class DocEvidence:
    """One doc or ADR file loaded as evidence."""

    type: str  # "doc" or "adr"
    path: str  # repo-relative POSIX path
    text: str


def load_docs(repo_path: Path) -> list[DocEvidence]:
    """Load README*, CONTRIBUTING*, docs/**/*.md and ADR folders."""
    results: list[DocEvidence] = []
    seen: set[str] = set()

    def add(path: Path, kind: str) -> None:
        rel = path.relative_to(repo_path).as_posix()
        if rel in seen or not path.is_file():
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        seen.add(rel)
        results.append(DocEvidence(type=kind, path=rel, text=text[:50_000]))

    for pattern in ("README*", "CONTRIBUTING*"):
        for path in sorted(repo_path.glob(pattern)):
            add(path, "doc")

    docs_dir = repo_path / "docs"
    if docs_dir.is_dir():
        for path in sorted(docs_dir.rglob("*.md")):
            rel = path.relative_to(repo_path).as_posix()
            if rel.startswith("docs/adr/"):
                continue  # picked up as ADRs below
            add(path, "doc")

    for adr_dir in ADR_DIRS:
        directory = repo_path / adr_dir
        if directory.is_dir():
            for path in sorted(directory.rglob("*.md")):
                add(path, "adr")

    return results
