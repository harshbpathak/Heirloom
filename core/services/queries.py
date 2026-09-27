"""Read-side query services shared by the API, CLI and MCP server."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.analysis.impact import ImpactEntry, compute_impact
from core.analysis.ownership import is_inactive
from core.errors import FileNotFoundInRepoError
from core.models.db_models import (
    Author,
    Commit,
    CommitFile,
    Coupling,
    Decision,
    DecisionEvidence,
    DecisionFile,
    Evidence,
    File,
    Import,
    Ownership,
    Repo,
)
from core.models.schemas import (
    CompactDecision,
    EvidenceRef,
    HolderSchema,
    ImpactItem,
)


def get_file_or_raise(session: Session, repo_id: str, path: str) -> File:
    """Look up a file row by path, raising a clear error when absent."""
    row = session.scalar(select(File).where(File.repo_id == repo_id, File.path == path))
    if row is None:
        raise FileNotFoundInRepoError(
            f"Path '{path}' does not exist in repo '{repo_id}'. "
            "Check the path is repo-relative and the repo has been ingested."
        )
    return row


def holders_for_file(session: Session, file_row: File, limit: int = 3) -> list[HolderSchema]:
    """Top knowledge holders for a file (names only, never emails — spec F4)."""
    rows = session.execute(
        select(Ownership, Author.canonical_name)
        .join(Author, Author.id == Ownership.author_id)
        .where(Ownership.file_id == file_row.id)
        .order_by(Ownership.ownership.desc())
        .limit(limit)
    ).all()
    holders = []
    for own, name in rows:
        # "Last active" is the person's latest commit anywhere in the repo.
        last = session.scalar(
            select(func.max(Commit.date)).where(Commit.author_id == own.author_id)
        )
        holders.append(
            HolderSchema(
                name=name,
                ownership=own.ownership,
                last_active=last.date().isoformat() if last else None,
                inactive=is_inactive(last),
            )
        )
    return holders


def impact_for_file(session: Session, repo_id: str, path: str, limit: int = 10) -> list[ImpactItem]:
    """Impact set for a file with human-readable reasons (F3 step 4)."""
    get_file_or_raise(session, repo_id, path)
    files = {f.id: f.path for f in session.scalars(select(File).where(File.repo_id == repo_id))}

    importers: dict[str, set[str]] = {}
    for edge in session.scalars(select(Import)):
        src, dst = files.get(edge.src_file_id), files.get(edge.dst_file_id)
        if src and dst:
            importers.setdefault(dst, set()).add(src)

    coupling: dict[tuple[str, str], tuple[int, float]] = {}
    for row in session.scalars(select(Coupling)):
        a, b = files.get(row.file_a_id), files.get(row.file_b_id)
        if a and b:
            coupling[(a, b)] = (row.co_changes, row.score)

    changes: dict[str, int] = {}
    for fid, count in session.execute(
        select(CommitFile.file_id, func.count()).group_by(CommitFile.file_id)
    ).all():
        path_name = files.get(fid)
        if path_name:
            changes[path_name] = count

    entries: list[ImpactEntry] = compute_impact(path, importers, coupling, changes, limit=limit)
    return [ImpactItem(path=e.path, score=e.score, reason=e.reason) for e in entries]


def decisions_for_file(session: Session, repo_id: str, path: str) -> list[CompactDecision]:
    """Decisions linked to a file, newest first."""
    file_row = get_file_or_raise(session, repo_id, path)
    rows = session.scalars(
        select(Decision)
        .join(DecisionFile, DecisionFile.decision_id == Decision.id)
        .where(DecisionFile.file_id == file_row.id)
        .order_by(Decision.created_at.desc())
    ).all()
    return [compact_decision(session, d) for d in rows]


def compact_decision(session: Session, decision: Decision) -> CompactDecision:
    """Compact form of a decision with its evidence references."""
    evidence_rows = session.scalars(
        select(Evidence)
        .join(DecisionEvidence, DecisionEvidence.evidence_id == Evidence.id)
        .where(DecisionEvidence.decision_id == decision.id)
    ).all()
    return CompactDecision(
        id=str(decision.id),
        title=decision.title,
        reasoning=decision.reasoning or decision.summary,
        confidence=decision.confidence,  # type: ignore[arg-type]
        date=decision.created_at.date().isoformat() if decision.created_at else None,
        evidence=[EvidenceRef(type=e.type, ref=e.ref, url=e.url) for e in evidence_rows],  # type: ignore[arg-type]
    )


def activity_for_file(session: Session, file_row: File) -> list[dict[str, Any]]:
    """Commits per month for the Why Card timeline."""
    rows = session.execute(
        select(Commit.date)
        .join(CommitFile, CommitFile.commit_hash == Commit.hash)
        .where(CommitFile.file_id == file_row.id)
    ).all()
    counts: dict[str, int] = {}
    for (date,) in rows:
        month = date.strftime("%Y-%m")
        counts[month] = counts.get(month, 0) + 1
    return [{"month": m, "commits": c} for m, c in sorted(counts.items())]


def repo_tree(session: Session, repo_id: str) -> dict[str, Any]:
    """Nested directory tree with loc, bus_factor, at_risk and top holders per file."""
    holder_rows = session.execute(
        select(Ownership.file_id, Author.canonical_name, Ownership.ownership)
        .join(Author, Author.id == Ownership.author_id)
        .where(Author.repo_id == repo_id)
        .order_by(Ownership.ownership.desc())
    ).all()
    holders_by_file: dict[int, list[dict[str, Any]]] = {}
    for fid, name, ownership in holder_rows:
        bucket = holders_by_file.setdefault(fid, [])
        if len(bucket) < 3:
            bucket.append({"name": name, "ownership": round(ownership, 3)})

    root: dict[str, Any] = {"name": "", "type": "dir", "children": {}, "loc": 0}
    for f in session.scalars(select(File).where(File.repo_id == repo_id)):
        parts = f.path.split("/")
        node = root
        for part in parts[:-1]:
            node = node["children"].setdefault(
                part, {"name": part, "type": "dir", "children": {}, "loc": 0}
            )
        node["children"][parts[-1]] = {
            "name": parts[-1],
            "type": "file",
            "path": f.path,
            "loc": f.loc,
            "bus_factor": f.bus_factor,
            "at_risk": f.at_risk,
            "language": f.language,
            "holders": holders_by_file.get(f.id, []),
        }
    return _finalize_tree(root)


def _finalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    """Convert children maps to sorted lists and roll up LOC."""
    if node["type"] == "file":
        return node
    children = [_finalize_tree(c) for c in node["children"].values()]
    children.sort(key=lambda c: (c["type"] != "dir", c["name"].lower()))
    node["children"] = children
    node["loc"] = sum(c["loc"] for c in children)
    return node


def risk_report(session: Session, repo_id: str, limit: int = 20) -> dict[str, Any]:
    """Repo-wide at-risk report: risky files plus concentration by person."""
    files = session.scalars(select(File).where(File.repo_id == repo_id)).all()
    at_risk = sorted((f for f in files if f.at_risk), key=lambda f: -f.loc)
    bf1 = [f for f in files if f.bus_factor == 1]
    total_loc = sum(f.loc for f in files)

    concentration = people_concentration(session, repo_id)
    return {
        "at_risk_files": [
            {"path": f.path, "loc": f.loc, "bus_factor": f.bus_factor} for f in at_risk[:limit]
        ],
        "bus_factor_1_files": len(bf1),
        "bus_factor_1_loc_pct": round(100 * sum(f.loc for f in bf1) / total_loc, 1)
        if total_loc
        else 0.0,
        "top_people": concentration[:5],
    }


def people_concentration(session: Session, repo_id: str) -> list[dict[str, Any]]:
    """Authors ranked by how much code they solely own."""
    last_active = dict(
        session.execute(
            select(Commit.author_id, func.max(Commit.date))
            .where(Commit.repo_id == repo_id)
            .group_by(Commit.author_id)
        ).all()
    )
    rows = session.execute(
        select(Author.id, Author.canonical_name, Ownership.ownership, File.loc)
        .join(Ownership, Ownership.author_id == Author.id)
        .join(File, File.id == Ownership.file_id)
        .where(Author.repo_id == repo_id)
    ).all()
    stats: dict[str, dict[str, Any]] = {}
    for author_id, name, ownership, loc in rows:
        last = last_active.get(author_id)
        entry = stats.setdefault(
            name,
            {
                "name": name,
                "owned_loc": 0.0,
                "files_over_40pct": 0,
                "last_active": last.date().isoformat() if last else None,
                "inactive": is_inactive(last),
            },
        )
        entry["owned_loc"] += ownership * loc
        if ownership > 0.4:
            entry["files_over_40pct"] += 1
    result = sorted(stats.values(), key=lambda e: -e["owned_loc"])
    for entry in result:
        entry["owned_loc"] = round(entry["owned_loc"])
    return result


def repo_stats(session: Session, repo_id: str) -> dict[str, Any]:
    """Stored repo stats (computed at ingest time)."""
    repo = session.get(Repo, repo_id)
    if repo is None or not repo.stats_json:
        return {}
    result = json.loads(repo.stats_json)
    assert isinstance(result, dict)
    return result
