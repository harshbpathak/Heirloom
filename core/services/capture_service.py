"""Decision capture service shared by the web form, CLI and MCP (spec F9).

Each captured decision is saved to SQLite (manual, high confidence) and
written as a Markdown record to ``.heirloom/decisions/`` in the target repo.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.decisions.capture import DecisionRecord, next_record_id, write_decision_record
from core.errors import ValidationFailedError
from core.models.db_models import Decision, DecisionEvidence, DecisionFile, Evidence, File, Repo
from core.timeutil import utcnow


def record_decision(
    session: Session,
    repo_id: str,
    title: str,
    files: list[str],
    reasoning: str,
    alternatives: str | None = None,
    author: str | None = None,
    skill_hash: str | None = None,
    repo_path: Path | None = None,
) -> tuple[int, str | None]:
    """Record a manual decision. Returns (decision_id, record_file_path).

    ``record_file_path`` is None when the target repo's working tree is not
    available (e.g. demo snapshots), and the decision then lives only in SQLite.
    """
    title = title.strip()
    if not title:
        raise ValidationFailedError("Decision title must not be empty")
    if len(title) > 80:
        raise ValidationFailedError("Decision title must be at most 80 characters")
    if not reasoning.strip():
        raise ValidationFailedError("Decision reasoning must not be empty")

    now = utcnow()
    decision = Decision(
        repo_id=repo_id,
        title=title,
        summary=reasoning.strip()[:300],
        reasoning=reasoning.strip(),
        alternatives=alternatives,
        confidence="high",
        created_at=now,
        source="manual",
        skill_hash=skill_hash,
        author=author,
    )
    session.add(decision)
    session.flush()

    for path in files:
        file_row = session.scalar(select(File).where(File.repo_id == repo_id, File.path == path))
        if file_row is not None:
            session.add(DecisionFile(decision_id=decision.id, file_id=file_row.id))

    record_path: str | None = None
    if repo_path is not None and repo_path.is_dir():
        record = DecisionRecord(
            id=next_record_id(repo_path),
            title=title,
            date=date.today(),
            files=files,
            confidence="high",
            source="manual",
            author=author,
            skill_hash=skill_hash,
            context="Recorded via Heirloom decision capture.",
            decision=title,
            reasoning=reasoning.strip(),
            alternatives=alternatives or "",
        )
        written = write_decision_record(repo_path, record)
        record_path = written.relative_to(repo_path).as_posix()

    ref = record_path or f"decision:{decision.id}"
    evidence = Evidence(
        repo_id=repo_id,
        type="manual",
        ref=ref,
        url=None,
        text=f"{title}\n\n{reasoning}",
        date=now,
    )
    session.add(evidence)
    session.flush()
    session.add(DecisionEvidence(decision_id=decision.id, evidence_id=evidence.id))
    session.flush()
    return decision.id, record_path


def local_repo_path(session: Session, repo_id: str) -> Path | None:
    """Working-tree path for a repo: its local source or its clone cache."""
    from core.config import get_settings
    from core.ingest.github_prs import parse_github_source

    repo = session.get(Repo, repo_id)
    if repo is None:
        return None
    gh = parse_github_source(repo.source)
    if gh is None:
        path = Path(repo.source).expanduser()
        return path if path.is_dir() else None
    cached = get_settings().cache_dir / f"{gh[0]}__{gh[1]}"
    return cached if cached.is_dir() else None
