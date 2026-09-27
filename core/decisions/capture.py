"""Decision capture: write/read `.heirloom/decisions/NNNN-slug.md` files (spec F9, §10.4)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import yaml
from slugify import slugify

DECISIONS_DIR = ".heirloom/decisions"

TEMPLATE = """---
{front_matter}---

## Context
{context}

## Decision
{decision}

## Reasoning
{reasoning}

## Alternatives considered
{alternatives}
"""


@dataclass
class DecisionRecord:
    """A decision record as stored in a Markdown file in the target repo."""

    id: str
    title: str
    date: date
    files: list[str] = field(default_factory=list)
    confidence: str = "high"
    source: str = "manual"
    author: str | None = None
    skill_hash: str | None = None
    context: str = ""
    decision: str = ""
    reasoning: str = ""
    alternatives: str = ""


def next_record_id(repo_path: Path) -> str:
    """Next zero-padded record id (0001, 0002, ...) in the decisions folder."""
    folder = repo_path / DECISIONS_DIR
    highest = 0
    if folder.is_dir():
        for path in folder.glob("*.md"):
            match = re.match(r"^(\d{4})-", path.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return f"{highest + 1:04d}"


def write_decision_record(repo_path: Path, record: DecisionRecord) -> Path:
    """Write a decision record to ``.heirloom/decisions/NNNN-slug.md``."""
    folder = repo_path / DECISIONS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    front = {
        "id": record.id,
        "title": record.title,
        "date": record.date.isoformat(),
        "files": record.files,
        "confidence": record.confidence,
        "source": record.source,
        "author": record.author or "",
        "skill_hash": record.skill_hash or "",
    }
    content = TEMPLATE.format(
        front_matter=yaml.safe_dump(front, sort_keys=False, allow_unicode=True),
        context=record.context or "Not recorded.",
        decision=record.decision or record.title,
        reasoning=record.reasoning or "Not recorded.",
        alternatives=record.alternatives or "None recorded.",
    )
    filename = f"{record.id}-{slugify(record.title)[:60]}.md"
    path = folder / filename
    path.write_text(content, encoding="utf-8")
    return path


_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def parse_decision_record(text: str) -> DecisionRecord | None:
    """Parse a decision Markdown file back into a record (round-trip, F9).

    Returns None when the file has no valid YAML front matter with a title.
    """
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return None
    try:
        front = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(front, dict) or not front.get("title"):
        return None

    body = text[match.end():]
    sections = _split_sections(body)
    raw_date = front.get("date")
    if isinstance(raw_date, date):
        record_date = raw_date
    else:
        try:
            record_date = datetime.fromisoformat(str(raw_date)).date()
        except (ValueError, TypeError):
            record_date = date.today()

    return DecisionRecord(
        id=str(front.get("id", "")),
        title=str(front["title"]),
        date=record_date,
        files=[str(f) for f in (front.get("files") or [])],
        confidence=str(front.get("confidence", "high")),
        source=str(front.get("source", "manual")),
        author=str(front.get("author") or "") or None,
        skill_hash=str(front.get("skill_hash") or "") or None,
        context=sections.get("context", ""),
        decision=sections.get("decision", ""),
        reasoning=sections.get("reasoning", ""),
        alternatives=sections.get("alternatives considered", ""),
    )


def _split_sections(body: str) -> dict[str, str]:
    """Split a record body into its ``## Heading`` sections (lower-cased keys)."""
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(body))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[m.group(1).strip().lower()] = body[m.end():end].strip()
    return sections


def load_decision_records(repo_path: Path) -> list[tuple[str, DecisionRecord]]:
    """Load all decision records from the repo; returns (relative_path, record)."""
    folder = repo_path / DECISIONS_DIR
    if not folder.is_dir():
        return []
    results: list[tuple[str, DecisionRecord]] = []
    for path in sorted(folder.glob("*.md")):
        try:
            record = parse_decision_record(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if record:
            results.append((f"{DECISIONS_DIR}/{path.name}", record))
    return results
