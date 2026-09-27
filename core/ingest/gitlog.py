"""Commit-log extraction via ``git log --numstat`` (spec F1 step 3)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

FIELD_SEP = "\x1f"
RECORD_SEP = "\x1e"


@dataclass
class LogEntry:
    """One parsed commit: metadata plus per-file line counts."""

    hash: str
    author_name: str
    author_email: str
    date: datetime
    message: str
    files: list[tuple[str, int, int]] = field(default_factory=list)  # (path, added, deleted)


def read_git_log(
    repo_path: Path,
    max_commits: int = 2000,
    since: str | None = None,
    after_commit: str | None = None,
) -> list[LogEntry]:
    """Read the commit log, newest first.

    ``after_commit`` limits output to commits made after the given hash
    (used for incremental re-ingestion). Merge commits are included but
    carry no numstat lines.
    """
    # The record separator LEADS each record so a commit's numstat lines
    # (printed after the format string) stay inside the same record.
    fmt = RECORD_SEP + FIELD_SEP.join(["%H", "%an", "%ae", "%aI", "%B"])
    cmd = ["git", "log", f"--max-count={max_commits}", f"--pretty=format:{fmt}", "--numstat"]
    if since:
        cmd.append(f"--since={since}")
    if after_commit:
        cmd.append(f"{after_commit}..HEAD")
    raw = subprocess.run(cmd, cwd=repo_path, capture_output=True, check=True).stdout.decode(
        "utf-8", errors="replace"
    )

    entries: list[LogEntry] = []
    for record in raw.split(RECORD_SEP):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split(FIELD_SEP)
        if len(parts) < 5:
            continue
        commit_hash, author_name, author_email, date_iso, rest = (
            parts[0].strip(),
            parts[1],
            parts[2],
            parts[3],
            FIELD_SEP.join(parts[4:]),
        )
        message, files = _split_message_and_numstat(rest)
        try:
            date = datetime.fromisoformat(date_iso).replace(tzinfo=None)
        except ValueError:
            continue
        entries.append(
            LogEntry(
                hash=commit_hash,
                author_name=author_name,
                author_email=author_email,
                date=date,
                message=message,
                files=files,
            )
        )
    return entries


def _split_message_and_numstat(rest: str) -> tuple[str, list[tuple[str, int, int]]]:
    """Split the tail of a log record into the message body and numstat rows."""
    lines = rest.split("\n")
    message_lines: list[str] = []
    files: list[tuple[str, int, int]] = []
    for line in lines:
        cols = line.split("\t")
        if len(cols) == 3 and _is_numstat(cols[0]) and _is_numstat(cols[1]):
            added = int(cols[0]) if cols[0] != "-" else 0
            deleted = int(cols[1]) if cols[1] != "-" else 0
            path = _normalize_numstat_path(cols[2])
            files.append((path, added, deleted))
        else:
            message_lines.append(line)
    return "\n".join(message_lines).strip(), files


def _is_numstat(value: str) -> bool:
    return value == "-" or value.isdigit()


def _normalize_numstat_path(path: str) -> str:
    """Resolve rename syntax like ``old => new`` or ``dir/{old => new}/f``."""
    if "=>" not in path:
        return path
    if "{" in path and "}" in path:
        prefix, _, tail = path.partition("{")
        change, _, suffix = tail.partition("}")
        new = change.split("=>")[-1].strip()
        combined = f"{prefix}{new}{suffix}"
        return combined.replace("//", "/")
    return path.split("=>")[-1].strip()


def head_commit(repo_path: Path) -> str | None:
    """Return the current HEAD hash, or None for an empty repo."""
    try:
        out = (
            subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, check=True
            )
            .stdout.decode()
            .strip()
        )
        return out or None
    except subprocess.CalledProcessError:
        return None


def default_branch(repo_path: Path) -> str:
    """Best-effort current branch name, defaulting to ``main``."""
    try:
        out = (
            subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )
            .stdout.decode()
            .strip()
        )
        return out or "main"
    except subprocess.CalledProcessError:
        return "main"
