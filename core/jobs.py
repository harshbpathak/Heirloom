"""Background ingestion jobs with progress reporting (spec F1, §9.1).

Jobs run in a thread; status lives in a small standalone SQLite database in
``HEIRLOOM_HOME`` so any API worker can answer ``GET /api/jobs/{id}``.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from core.errors import JobNotFoundError
from core.models.db_models import Base, Job
from core.models.schemas import JobStatus
from core.timeutil import utcnow

_lock = threading.Lock()
_engines: dict[str, Engine] = {}


def _jobs_engine(settings: Settings) -> Engine:
    path = settings.heirloom_home / "jobs.sqlite"
    key = str(path)
    with _lock:
        if key not in _engines:
            path.parent.mkdir(parents=True, exist_ok=True)
            engine = create_engine(f"sqlite:///{path}", future=True)
            Base.metadata.create_all(engine)
            _engines[key] = engine
        return _engines[key]


def create_job(repo_id: str, kind: str = "ingest", settings: Settings | None = None) -> str:
    """Create a pending job row and return its id."""
    settings = settings or get_settings()
    job_id = uuid.uuid4().hex[:12]
    with Session(_jobs_engine(settings)) as session:
        session.add(
            Job(
                id=job_id,
                repo_id=repo_id,
                kind=kind,
                status="pending",
                progress=0,
                message="queued",
            )
        )
        session.commit()
    return job_id


def update_job(
    job_id: str,
    status: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    settings: Settings | None = None,
) -> None:
    """Update a job's status/progress/message."""
    settings = settings or get_settings()
    with Session(_jobs_engine(settings)) as session:
        job = session.get(Job, job_id)
        if job is None:
            return
        if status is not None:
            job.status = status
            if status == "running" and job.started_at is None:
                job.started_at = utcnow()
            if status in ("done", "failed"):
                job.finished_at = utcnow()
        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        session.commit()


def get_job(job_id: str, settings: Settings | None = None) -> JobStatus:
    """Fetch a job's status; raises :class:`JobNotFoundError` when missing."""
    settings = settings or get_settings()
    with Session(_jobs_engine(settings)) as session:
        job = session.get(Job, job_id)
        if job is None:
            raise JobNotFoundError(f"No job with id '{job_id}'")
        return JobStatus(
            id=job.id,
            repo_id=job.repo_id,
            kind=job.kind,
            status=job.status,
            progress=job.progress,
            message=job.message,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )


def run_ingest_job(
    source: str,
    since: str | None = None,
    max_commits: int | None = None,
    settings: Settings | None = None,
) -> tuple[str, str]:
    """Start an ingestion job in a background thread. Returns (repo_id, job_id)."""
    from core.db import repo_id_from_source
    from core.ingest.pipeline import ingest_repo

    settings = settings or get_settings()
    repo_id = repo_id_from_source(source)
    job_id = create_job(repo_id, settings=settings)

    def worker() -> None:
        update_job(job_id, status="running", message="starting", settings=settings)
        try:
            ingest_repo(
                source,
                since=since,
                max_commits=max_commits,
                settings=settings,
                progress=lambda pct, msg: update_job(
                    job_id, progress=pct, message=msg, settings=settings
                ),
            )
            update_job(job_id, status="done", progress=100, message="done", settings=settings)
        except Exception as exc:  # report any failure through job status
            update_job(job_id, status="failed", message=str(exc)[:500], settings=settings)

    threading.Thread(target=worker, daemon=True).start()
    return repo_id, job_id


def list_jobs_for_repo(repo_id: str, settings: Settings | None = None) -> list[JobStatus]:
    """All jobs for a repo, newest first."""
    settings = settings or get_settings()
    with Session(_jobs_engine(settings)) as session:
        jobs = list(session.scalars(select(Job).where(Job.repo_id == repo_id)).all())
        jobs.sort(key=lambda j: j.started_at or datetime.min, reverse=True)
        return [
            JobStatus(
                id=j.id,
                repo_id=j.repo_id,
                kind=j.kind,
                status=j.status,
                progress=j.progress,
                message=j.message,
                started_at=j.started_at,
                finished_at=j.finished_at,
            )
            for j in jobs
        ]
