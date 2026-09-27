"""Heirloom REST API (spec §9.1). All logic lives in ``core``; routes are thin."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from core import jobs
from core.config import get_settings
from core.db import list_repo_ids, session_for
from core.errors import HeirloomError, RepoNotFoundError, ValidationFailedError
from core.llm.provider import get_provider
from core.logging_config import configure_logging
from core.models.db_models import Decision, DecisionFile, File, Repo
from core.services.ask import ask as ask_service
from core.services.capture_service import local_repo_path, record_decision
from core.services.queries import (
    compact_decision,
    get_file_or_raise,
    holders_for_file,
    impact_for_file,
    people_concentration,
    repo_stats,
    repo_tree,
    risk_report,
)
from core.services.whycard import agent_context, build_why_card, why_card_markdown
from core.trails.builder import build_trail

configure_logging()

app = FastAPI(
    title="Heirloom API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json"
)


def _cors_origins() -> list[str]:
    """Origins allowed to call the API from a browser.

    ``CORS_ORIGINS`` is a comma-separated list (``*`` allows any origin, which is
    fine here: the API sets no cookies). The Vite dev server is always allowed.
    """
    extra = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
    if "*" in extra:
        return ["*"]
    return ["http://localhost:5173", "http://127.0.0.1:5173", *extra]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATUS_BY_CODE = {
    "repo_not_found": 404,
    "file_not_found": 404,
    "job_not_found": 404,
    "validation_failed": 422,
    "ingest_error": 400,
}


@app.exception_handler(HeirloomError)
async def heirloom_error_handler(_request: Request, exc: HeirloomError) -> JSONResponse:
    """Map core exceptions onto the error envelope from spec §9.1."""
    return JSONResponse(
        status_code=_STATUS_BY_CODE.get(exc.code, 500),
        content={"error": {"code": exc.code, "message": exc.message}},
    )


class IngestRequest(BaseModel):
    """Body of POST /api/repos."""

    source: str
    since: str | None = None
    max_commits: int | None = None


class AskRequest(BaseModel):
    """Body of POST /api/repos/{id}/ask."""

    question: str


class DecisionRequest(BaseModel):
    """Body of POST /api/repos/{id}/decisions."""

    title: str = Field(max_length=80)
    files: list[str] = Field(default_factory=list)
    reasoning: str
    alternatives: str | None = None
    author: str | None = None
    skill_hash: str | None = None


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Liveness plus which LLM backend is active."""
    settings = get_settings()
    return {"ok": True, "llm": get_provider(settings).name, "demo": settings.demo_mode}


@app.post("/api/repos")
def create_repo(body: IngestRequest) -> dict[str, str]:
    """Start ingesting a repo; returns ids for polling job progress."""
    settings = get_settings()
    if settings.demo_mode:
        raise ValidationFailedError(
            "Demo mode is read-only: ingestion is disabled (HEIRLOOM_DEMO=1)"
        )
    repo_id, job_id = jobs.run_ingest_job(body.source, body.since, body.max_commits, settings)
    return {"repo_id": repo_id, "job_id": job_id}


@app.get("/api/repos")
def list_repos() -> list[dict[str, Any]]:
    """All ingested repos with their stats."""
    settings = get_settings()
    result = []
    for repo_id in list_repo_ids(settings.db_dir):
        with session_for(repo_id, settings.db_dir) as session:
            repo = session.get(Repo, repo_id)
            if repo is None:
                continue
            result.append(
                {
                    "id": repo.id,
                    "name": repo.name,
                    "source": repo.source,
                    "ingested_at": repo.ingested_at.isoformat() if repo.ingested_at else None,
                    "stats": repo_stats(session, repo_id),
                }
            )
    return result


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict[str, Any]:
    """Progress of a background ingestion job."""
    return jobs.get_job(job_id).model_dump(mode="json")


@app.get("/api/repos/{repo_id}/tree")
def tree(repo_id: str) -> dict[str, Any]:
    """Nested dirs/files with loc, bus_factor, at_risk."""
    with session_for(repo_id) as session:
        _require_repo(session, repo_id)
        return repo_tree(session, repo_id)


@app.get("/api/repos/{repo_id}/why")
def why(repo_id: str, path: str, format: str = "json") -> Any:
    """The Why Card for one file (json, markdown or agent-context format)."""
    settings = get_settings()
    with session_for(repo_id) as session:
        _require_repo(session, repo_id)
        card = build_why_card(
            session,
            repo_id,
            path,
            repo_path=local_repo_path(session, repo_id),
            provider=get_provider(settings),
        )
        if format == "markdown":
            return {"markdown": why_card_markdown(card)}
        if format == "agent":
            return agent_context(card).model_dump()
        return card.model_dump()


@app.get("/api/repos/{repo_id}/who")
def who(repo_id: str, path: str) -> dict[str, Any]:
    """Knowledge holders and bus factor for one file."""
    with session_for(repo_id) as session:
        file_row = get_file_or_raise(session, repo_id, path)
        return {
            "path": path,
            "holders": [h.model_dump() for h in holders_for_file(session, file_row)],
            "bus_factor": file_row.bus_factor,
            "at_risk": file_row.at_risk,
        }


@app.get("/api/repos/{repo_id}/impact")
def impact(repo_id: str, path: str, limit: int = 10) -> dict[str, Any]:
    """Ranked impact set for one file."""
    with session_for(repo_id) as session:
        return {
            "path": path,
            "impact": [i.model_dump() for i in impact_for_file(session, repo_id, path, limit)],
        }


@app.get("/api/repos/{repo_id}/trail")
def trail(repo_id: str, topic: str | None = None, max_steps: int = 10) -> dict[str, Any]:
    """Onboarding trail, optionally focused on a topic."""
    settings = get_settings()
    with session_for(repo_id) as session:
        _require_repo(session, repo_id)
        result = build_trail(
            session,
            repo_id,
            topic=topic,
            max_steps=max_steps,
            repo_path=local_repo_path(session, repo_id),
            provider=get_provider(settings),
        )
        return result.model_dump()


@app.post("/api/repos/{repo_id}/ask")
def ask(repo_id: str, body: AskRequest) -> dict[str, Any]:
    """Answer a question about the repo with citations."""
    settings = get_settings()
    with session_for(repo_id) as session:
        _require_repo(session, repo_id)
        return ask_service(session, repo_id, body.question, get_provider(settings)).model_dump()


@app.get("/api/repos/{repo_id}/decisions")
def decisions(
    repo_id: str, q: str | None = None, file: str | None = None, limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    """Filterable decision list."""
    with session_for(repo_id) as session:
        _require_repo(session, repo_id)
        stmt = select(Decision).where(Decision.repo_id == repo_id)
        if file:
            file_row = get_file_or_raise(session, repo_id, file)
            stmt = stmt.join(DecisionFile, DecisionFile.decision_id == Decision.id).where(
                DecisionFile.file_id == file_row.id
            )
        rows = session.scalars(stmt.order_by(Decision.created_at.desc())).all()
        if q:
            needle = q.lower()
            rows = [
                d
                for d in rows
                if needle in d.title.lower()
                or needle in (d.summary or "").lower()
                or needle in (d.reasoning or "").lower()
            ]
        total = len(rows)
        page = rows[offset : offset + limit]
        return {
            "total": total,
            "items": [
                compact_decision(session, d).model_dump()
                | {
                    "source": d.source,
                    "summary": d.summary,
                    "alternatives": d.alternatives,
                    "files": _decision_files(session, d.id),
                }
                for d in page
            ],
        }


def _decision_files(session, decision_id: int) -> list[str]:
    rows = session.execute(
        select(File.path)
        .join(DecisionFile, DecisionFile.file_id == File.id)
        .where(DecisionFile.decision_id == decision_id)
    ).all()
    return [r[0] for r in rows]


@app.post("/api/repos/{repo_id}/decisions", status_code=201)
def create_decision(repo_id: str, body: DecisionRequest) -> dict[str, Any]:
    """Record a manual decision (web form entry point of F9)."""
    with session_for(repo_id) as session:
        _require_repo(session, repo_id)
        decision_id, record_path = record_decision(
            session,
            repo_id,
            body.title,
            body.files,
            body.reasoning,
            alternatives=body.alternatives,
            author=body.author,
            skill_hash=body.skill_hash,
            repo_path=local_repo_path(session, repo_id),
        )
        return {"id": str(decision_id), "record_path": record_path}


@app.get("/api/repos/{repo_id}/risk")
def risk(repo_id: str, limit: int = 20) -> dict[str, Any]:
    """Repo-wide at-risk report."""
    with session_for(repo_id) as session:
        _require_repo(session, repo_id)
        return risk_report(session, repo_id, limit)


@app.get("/api/repos/{repo_id}/people")
def people(repo_id: str) -> list[dict[str, Any]]:
    """Authors with concentration stats (names only, never emails)."""
    with session_for(repo_id) as session:
        _require_repo(session, repo_id)
        return people_concentration(session, repo_id)


def _require_repo(session, repo_id: str) -> None:
    if session.get(Repo, repo_id) is None:
        raise RepoNotFoundError(f"Repo '{repo_id}' has not been ingested")


def openapi_json() -> str:
    """The generated OpenAPI spec as JSON (linked from the README)."""
    return json.dumps(app.openapi(), indent=2)


def mount_web(dist: Path) -> None:
    """Serve the built web UI from ``dist`` with an SPA fallback.

    Deep links such as ``/repo/x/why`` must return ``index.html`` so the
    client router can handle them; unknown ``/api`` paths still 404 as JSON.
    """
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> Any:
        if full_path.startswith("api/"):
            return JSONResponse(
                status_code=404, content={"error": {"code": "not_found", "message": full_path}}
            )
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")
