"""Heirloom MCP server (spec §6), built with FastMCP.

Imports the same core library as the CLI and API — no duplicated logic.
Every tool validates paths, and every response stays under ~2000 tokens by
truncating lists and saying how many items were cut.
"""

from __future__ import annotations

import json
import os
from typing import Any

from fastmcp import FastMCP

from core.config import get_settings
from core.db import list_repo_ids, repo_id_from_source, session_for
from core.errors import HeirloomError
from core.llm.provider import get_provider

mcp = FastMCP(
    "heirloom",
    instructions=(
        "Heirloom explains why code is the way it is. Call ask_why before "
        "editing a file, impact_if_changed to see what a change affects, and "
        "record_decision after making a real design choice."
    ),
)

MAX_RESPONSE_CHARS = 8000  # ~2000 tokens


def _default_repo() -> str:
    """Pick the repo an agent most likely means.

    Order: ``HEIRLOOM_REPO`` env var, then the repo whose id matches the
    server's working directory (agents launch it from the project root),
    then the only ingested repo. Ambiguity is an error, never a guess.
    """
    ids = list_repo_ids()
    if not ids:
        raise HeirloomError("No repos ingested. Run `heirloom ingest <path-or-url>` first.")
    explicit = os.environ.get("HEIRLOOM_REPO", "").strip()
    if explicit:
        return repo_id_from_source(explicit) if os.path.isdir(explicit) else explicit
    cwd_id = repo_id_from_source(os.getcwd())
    if cwd_id in ids:
        return cwd_id
    if len(ids) == 1:
        return ids[0]
    raise HeirloomError(
        f"Several repos are ingested ({', '.join(ids)}); pass repo_id or set HEIRLOOM_REPO."
    )


def _repo_or_default(repo_id: str | None) -> str:
    return repo_id if repo_id else _default_repo()


def _error(exc: HeirloomError) -> dict[str, Any]:
    return {"error": {"code": exc.code, "message": exc.message}}


def _truncate(payload: dict[str, Any], list_keys: list[str]) -> dict[str, Any]:
    """Trim named list fields until the JSON stays under the size budget."""

    def size() -> int:
        return len(json.dumps(payload, default=str))

    cut_total = 0
    while size() > MAX_RESPONSE_CHARS:
        trimmed = False
        for key in list_keys:
            value = payload.get(key)
            if isinstance(value, list) and len(value) > 1:
                value.pop()
                cut_total += 1
                trimmed = True
                if size() <= MAX_RESPONSE_CHARS:
                    break
        if not trimmed:
            break
    if cut_total:
        payload["truncated"] = f"{cut_total} items cut to stay under the response size limit"
    return payload


@mcp.tool()
def ask_why(path: str, symbol: str | None = None, repo_id: str | None = None) -> dict[str, Any]:
    """Why Card for a file: summary, decisions (id, title, reasoning, confidence,
    evidence refs) and warnings. Call this before editing any file."""
    try:
        rid = _repo_or_default(repo_id)
        with session_for(rid) as session:
            from core.services.capture_service import local_repo_path
            from core.services.whycard import build_why_card

            card = build_why_card(
                session, rid, path, repo_path=local_repo_path(session, rid), provider=get_provider()
            )
        payload = {
            "path": card.path,
            "summary": card.summary,
            "summary_source": card.summary_source,
            "decisions": [
                {
                    "id": d.id,
                    "title": d.title,
                    "reasoning": d.reasoning[:300],
                    "confidence": d.confidence,
                    "evidence": [e.ref for e in d.evidence[:3]],
                }
                for d in card.decisions
            ],
            "warnings": [{"line": w.line, "text": w.text} for w in card.warnings],
            "bus_factor": card.bus_factor,
            "at_risk": card.at_risk,
        }
        return _truncate(payload, ["decisions", "warnings"])
    except HeirloomError as exc:
        return _error(exc)


@mcp.tool()
def who_knows(path: str, repo_id: str | None = None) -> dict[str, Any]:
    """Knowledge holders for a file: ownership percent, last active date,
    bus factor and the at_risk flag."""
    try:
        rid = _repo_or_default(repo_id)
        with session_for(rid) as session:
            from core.services.queries import get_file_or_raise, holders_for_file

            row = get_file_or_raise(session, rid, path)
            holders = holders_for_file(session, row)
        return {
            "path": path,
            "holders": [h.model_dump() for h in holders],
            "bus_factor": row.bus_factor,
            "at_risk": row.at_risk,
        }
    except HeirloomError as exc:
        return _error(exc)


@mcp.tool()
def impact_if_changed(path: str, limit: int = 10, repo_id: str | None = None) -> dict[str, Any]:
    """Ranked list of files likely affected if this file changes, with reasons."""
    try:
        rid = _repo_or_default(repo_id)
        with session_for(rid) as session:
            from core.services.queries import impact_for_file

            items = impact_for_file(session, rid, path, limit)
        return _truncate({"path": path, "impact": [i.model_dump() for i in items]}, ["impact"])
    except HeirloomError as exc:
        return _error(exc)


@mcp.tool()
def onboarding_trail(
    topic: str | None = None, max_steps: int = 10, repo_id: str | None = None
) -> dict[str, Any]:
    """Ordered reading path through the repo for onboarding, optionally topical."""
    try:
        rid = _repo_or_default(repo_id)
        with session_for(rid) as session:
            from core.services.capture_service import local_repo_path
            from core.trails.builder import build_trail

            result = build_trail(
                session,
                rid,
                topic=topic,
                max_steps=max_steps,
                repo_path=local_repo_path(session, rid),
                provider=get_provider(),
            )
        payload = {
            "topic": result.topic,
            "steps": [
                {
                    "path": s.path,
                    "reason": s.reason,
                    "reading_minutes": s.reading_minutes,
                    "decisions": [d.title for d in s.decisions],
                }
                for s in result.steps
            ],
        }
        return _truncate(payload, ["steps"])
    except HeirloomError as exc:
        return _error(exc)


@mcp.tool()
def search_decisions(query: str, limit: int = 8, repo_id: str | None = None) -> dict[str, Any]:
    """Search recorded decisions by keyword (BM25 over titles, reasoning, evidence)."""
    try:
        rid = _repo_or_default(repo_id)
        with session_for(rid) as session:
            from core.models.db_models import Decision
            from core.search.index import DecisionIndex
            from core.services.queries import compact_decision

            hits = DecisionIndex(session, rid).search(query, limit)
            items = [
                compact_decision(session, session.get(Decision, h.decision_id)).model_dump()
                for h in hits
            ]
        return _truncate({"query": query, "decisions": items}, ["decisions"])
    except HeirloomError as exc:
        return _error(exc)


@mcp.tool()
def record_decision(
    title: str,
    files: list[str],
    reasoning: str,
    alternatives: str | None = None,
    author: str | None = None,
    repo_id: str | None = None,
    skill_hash: str | None = None,
) -> dict[str, Any]:
    """Record a new design decision. Writes to Heirloom's database and to
    `.heirloom/decisions/NNNN-slug.md` in the target repo. Returns the new
    decision id and file path. `skill_hash` is the SHA-256 of the capturing
    skill's SKILL.md, stored in the record's front matter for auditability."""
    try:
        rid = _repo_or_default(repo_id)
        with session_for(rid) as session:
            from core.services.capture_service import local_repo_path
            from core.services.capture_service import record_decision as record

            decision_id, record_path = record(
                session,
                rid,
                title,
                files,
                reasoning,
                alternatives=alternatives,
                author=author,
                skill_hash=skill_hash,
                repo_path=local_repo_path(session, rid),
            )
        return {"id": str(decision_id), "record_path": record_path}
    except HeirloomError as exc:
        return _error(exc)


@mcp.tool()
def repo_risk_report(limit: int = 20, repo_id: str | None = None) -> dict[str, Any]:
    """At-risk files and the people with the highest knowledge concentration."""
    try:
        rid = _repo_or_default(repo_id)
        with session_for(rid) as session:
            from core.services.queries import risk_report

            report = risk_report(session, rid, limit)
        return _truncate(report, ["at_risk_files", "top_people"])
    except HeirloomError as exc:
        return _error(exc)


@mcp.resource("heirloom://repo/{repo_id}/why/{path*}")
def why_card_resource(repo_id: str, path: str) -> str:
    """The Why Card for a file as Markdown."""
    with session_for(repo_id) as session:
        from core.services.capture_service import local_repo_path
        from core.services.whycard import build_why_card, why_card_markdown

        card = build_why_card(
            session,
            repo_id,
            path,
            repo_path=local_repo_path(session, repo_id),
            provider=get_provider(),
        )
        return why_card_markdown(card)


@mcp.resource("heirloom://repo/{repo_id}/decisions")
def decisions_resource(repo_id: str) -> str:
    """Index of all recorded decisions for a repo."""
    from sqlalchemy import select

    from core.models.db_models import Decision

    with session_for(repo_id) as session:
        rows = session.scalars(
            select(Decision).where(Decision.repo_id == repo_id).order_by(Decision.created_at.desc())
        ).all()
        lines = [f"# Decisions in {repo_id}", ""]
        for d in rows:
            lines.append(f"- [{d.id}] {d.title} ({d.confidence}, {d.source})")
        return "\n".join(lines)


def run_server(http: bool = False, port: int | None = None) -> None:
    """Run over stdio (default) or streamable HTTP with --http."""
    if http:
        mcp.run(transport="http", port=port or get_settings().mcp_http_port)
    else:
        mcp.run()


if __name__ == "__main__":
    run_server()
