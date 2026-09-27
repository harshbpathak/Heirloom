"""PR guard report building and rendering (spec F10).

Pure functions over an ingested repo so the comment body can be
snapshot-tested; ``action/entrypoint.py`` handles git, env and the GitHub API.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.ingest.comments import extract_intent_comments
from core.models.db_models import File
from core.models.schemas import CompactDecision, HolderSchema
from core.services.queries import decisions_for_file, holders_for_file, impact_for_file

COMMENT_MARKER = "<!-- heirloom-pr-guard -->"
DO_NOT_WINDOW = 10
MAX_DECISIONS_PER_FILE = 5
MAX_IMPACT_PER_FILE = 5

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_changed_lines(diff_text: str) -> dict[str, list[int]]:
    """Map each file in a ``git diff -U0`` to the new-side line numbers it touches.

    Deleted-only hunks (count 0) record the line they sit next to, so a DO NOT
    comment beside a deletion still triggers a warning.
    """
    changed: dict[str, list[int]] = {}
    current: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            current = None if target == "/dev/null" else target.removeprefix("b/")
            if current is not None:
                changed.setdefault(current, [])
            continue
        match = _HUNK_RE.match(line)
        if match and current is not None:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            changed[current].extend(range(start, start + max(count, 1)))
    return changed


@dataclass
class FileReport:
    """Everything the PR comment says about one changed file."""

    path: str
    known: bool
    bus_factor: int | None = None
    at_risk: bool = False
    holders: list[HolderSchema] = field(default_factory=list)
    decisions: list[CompactDecision] = field(default_factory=list)
    impact_outside_pr: list[tuple[str, str]] = field(default_factory=list)
    do_not_warnings: list[tuple[int, str]] = field(default_factory=list)


@dataclass
class GuardReport:
    """The full PR guard result."""

    files: list[FileReport]
    strict_failures: list[str] = field(default_factory=list)


def build_report(
    session: Session,
    repo_id: str,
    repo_path: Path,
    changed: dict[str, list[int]],
    reviewers: list[str] | None = None,
    strict: bool = False,
) -> GuardReport:
    """Build the guard report for the files a PR changes."""
    reviewers = reviewers or []
    pr_files = set(changed)
    reports: list[FileReport] = []
    failures: list[str] = []

    for path in sorted(changed):
        row = session.scalar(select(File).where(File.repo_id == repo_id, File.path == path))
        if row is None:
            reports.append(FileReport(path=path, known=False))
            continue
        holders = holders_for_file(session, row)
        report = FileReport(
            path=path,
            known=True,
            bus_factor=row.bus_factor,
            at_risk=row.at_risk,
            holders=holders,
            decisions=decisions_for_file(session, repo_id, path)[:MAX_DECISIONS_PER_FILE],
            impact_outside_pr=[
                (i.path, i.reason)
                for i in impact_for_file(session, repo_id, path, limit=20)
                if i.path not in pr_files
            ][:MAX_IMPACT_PER_FILE],
            do_not_warnings=_do_not_near(repo_path, path, row.language, changed[path]),
        )
        reports.append(report)
        if strict and row.at_risk and not reviewer_is_holder(reviewers, holders):
            failures.append(
                f"{path} is at risk and no knowledge holder "
                f"({', '.join(h.name for h in holders) or 'unknown'}) is a requested reviewer"
            )
    return GuardReport(files=reports, strict_failures=failures)


def _do_not_near(
    repo_path: Path, path: str, language: str | None, lines: list[int]
) -> list[tuple[int, str]]:
    """DO NOT comments within 10 lines of any changed line."""
    hits = []
    for c in extract_intent_comments(repo_path, path, language):
        if "DO NOT" in c.text.upper() and any(abs(c.line - n) <= DO_NOT_WINDOW for n in lines):
            hits.append((c.line, c.text))
    return hits


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def reviewer_is_holder(reviewers: list[str], holders: list[HolderSchema]) -> bool:
    """Loose match between GitHub logins and git author names.

    Logins and names differ, so a reviewer counts when the normalized login
    equals the normalized full name or contains the first or last name
    (3+ chars). This can miss people; strict mode is opt-in for that reason.
    """
    for login in map(_norm, reviewers):
        for holder in holders:
            name = _norm(holder.name)
            parts = [_norm(p) for p in holder.name.split() if len(_norm(p)) >= 3]
            if login == name or any(p in login for p in parts):
                return True
    return False


def _badge(report: FileReport) -> str:
    if report.bus_factor in (None, 0):
        return "⚪ bus factor unknown"
    if report.bus_factor == 1:
        return "🔴 bus factor 1" + (" · **AT RISK**" if report.at_risk else "")
    if report.bus_factor == 2:
        return "🟠 bus factor 2"
    return f"🟢 bus factor {report.bus_factor}"


def render_comment(report: GuardReport) -> str:
    """Render the single PR comment (Markdown, with an update marker)."""
    lines = [COMMENT_MARKER, "## 🏺 Heirloom PR guard", ""]
    if not report.files:
        lines.append("No changed files.")
    for f in report.files:
        lines.append(f"### `{f.path}`")
        if not f.known:
            lines += ["New or unanalyzed file — Heirloom has no history for it yet.", ""]
            continue
        holders = ", ".join(f"{h.name} ({h.ownership:.0%})" for h in f.holders) or "unknown"
        lines.append(f"{_badge(f)} · knowledge holders: {holders}")
        for line_no, text in f.do_not_warnings:
            lines.append(f"> ⚠️ **DO NOT comment near your change** (line {line_no}): {text}")
        if f.decisions:
            lines.append("")
            lines.append("**Decisions this change might conflict with:**")
            for d in f.decisions:
                refs = ", ".join(e.url or f"{e.type}:{e.ref}" for e in d.evidence[:2])
                why = f" — {d.reasoning[:160]}" if d.reasoning and d.reasoning != d.title else ""
                lines.append(f"- {d.title} _({d.confidence})_{why} [{refs}]")
        if f.impact_outside_pr:
            lines.append("")
            lines.append("**Impacted files not in this PR:**")
            for p, reason in f.impact_outside_pr:
                lines.append(f"- `{p}` — {reason}")
        lines.append("")
    if report.strict_failures:
        lines.append("### ❌ Strict mode")
        lines += [f"- {msg}" for msg in report.strict_failures]
        lines.append("")
    lines.append("<sub>Generated by Heirloom · works offline, no LLM required.</sub>")
    return "\n".join(lines) + "\n"
