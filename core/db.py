"""Database session management: one SQLite file per ingested repo."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings
from core.errors import RepoNotFoundError
from core.models.db_models import Base

_engines: dict[str, Engine] = {}


def repo_id_from_source(source: str) -> str:
    """Derive a stable repo id: ``owner__name`` for GitHub URLs, else a folder slug."""
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", source.strip())
    if match:
        return f"{match.group(1)}__{match.group(2)}"
    name = Path(source).name or "repo"
    return re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-").lower() or "repo"


def db_path_for(repo_id: str, db_dir: Path | None = None) -> Path:
    """Path of the SQLite file for a repo id."""
    base = db_dir if db_dir is not None else get_settings().db_dir
    return base / f"{repo_id}.sqlite"


def get_engine(repo_id: str, db_dir: Path | None = None, create: bool = False) -> Engine:
    """Return (and cache) the engine for a repo, creating tables when ``create``.

    Raises :class:`RepoNotFoundError` when the database does not exist and
    ``create`` is false.
    """
    path = db_path_for(repo_id, db_dir)
    key = str(path)
    if key in _engines:
        return _engines[key]
    if not path.exists() and not create:
        raise RepoNotFoundError(f"Repo '{repo_id}' has not been ingested (no database at {path})")
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(engine)
    _engines[key] = engine
    return engine


@contextmanager
def session_for(repo_id: str, db_dir: Path | None = None, create: bool = False) -> Iterator[Session]:
    """Context manager yielding a session bound to the repo's database."""
    engine = get_engine(repo_id, db_dir, create=create)
    factory = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def list_repo_ids(db_dir: Path | None = None) -> list[str]:
    """List ids of all ingested repos (one per SQLite file)."""
    base = db_dir if db_dir is not None else get_settings().db_dir
    if not base.exists():
        return []
    return sorted(p.stem for p in base.glob("*.sqlite"))


def dispose_engines() -> None:
    """Dispose all cached engines (used by tests to release file handles)."""
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()
