"""Full knowledge-base export as Markdown or JSON (CLI `heirloom export`)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.db_models import Decision, File, Repo
from core.services.queries import compact_decision, repo_stats


def export_json(session: Session, repo_id: str) -> str:
    """Export repo stats, files and decisions as a JSON document."""
    return json.dumps(_gather(session, repo_id), indent=2, ensure_ascii=False)


def export_markdown(session: Session, repo_id: str) -> str:
    """Export the knowledge base as a single Markdown document."""
    data = _gather(session, repo_id)
    lines = [f"# Heirloom knowledge base: {data['repo']['name']}", ""]
    stats = data["stats"]
    if stats:
        lines.append(
            f"{stats.get('files', 0)} files · {stats.get('loc', 0)} LOC · "
            f"{stats.get('decisions', 0)} decisions · "
            f"{stats.get('bus_factor_1_loc_pct', 0)}% of LOC has bus factor 1"
        )
        lines.append("")
    lines.append("## Decisions")
    for d in data["decisions"]:
        lines.append(f"### {d['title']}")
        lines.append(f"*Confidence: {d['confidence']} · {d['date'] or 'unknown date'}*")
        if d["reasoning"]:
            lines.append(d["reasoning"])
        if d["evidence"]:
            lines.append("Evidence: " + ", ".join(e["ref"] for e in d["evidence"]))
        lines.append("")
    lines.append("## At-risk files")
    risky = [f for f in data["files"] if f["at_risk"]]
    if risky:
        for f in risky:
            lines.append(f"- {f['path']} (bus factor {f['bus_factor']})")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _gather(session: Session, repo_id: str) -> dict[str, Any]:
    repo = session.get(Repo, repo_id)
    decisions = session.scalars(
        select(Decision).where(Decision.repo_id == repo_id).order_by(Decision.created_at.desc())
    ).all()
    files = session.scalars(select(File).where(File.repo_id == repo_id)).all()
    return {
        "repo": {
            "id": repo_id,
            "name": repo.name if repo else repo_id,
            "source": repo.source if repo else "",
        },
        "stats": repo_stats(session, repo_id),
        "decisions": [compact_decision(session, d).model_dump() for d in decisions],
        "files": [
            {"path": f.path, "loc": f.loc, "bus_factor": f.bus_factor, "at_risk": f.at_risk}
            for f in files
        ],
    }
