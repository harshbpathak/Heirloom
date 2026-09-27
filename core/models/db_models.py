"""SQLAlchemy 2.x ORM models implementing the Heirloom data model (spec §8).

One SQLite database per repo lives at ``~/.heirloom/db/<repo_id>.sqlite``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all Heirloom tables."""


class Repo(Base):
    """A git repository Heirloom has ingested."""

    __tablename__ = "repos"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    default_branch: Mapped[str] = mapped_column(String, default="main")
    last_ingested_commit: Mapped[str | None] = mapped_column(String, nullable=True)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stats_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class File(Base):
    """A source file in the repo with analysis results attached."""

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repos.id"), index=True)
    path: Mapped[str] = mapped_column(String, index=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    loc: Mapped[int] = mapped_column(Integer, default=0)
    is_entry_point: Mapped[bool] = mapped_column(Boolean, default=False)
    fan_in: Mapped[int] = mapped_column(Integer, default=0)
    fan_out: Mapped[int] = mapped_column(Integer, default=0)
    bus_factor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    at_risk: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_source: Mapped[str] = mapped_column(String, default="none")  # llm|comment|none

    __table_args__ = (UniqueConstraint("repo_id", "path", name="uq_files_repo_path"),)


class Author(Base):
    """A canonical author identity; aliases are merged during ingestion."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repos.id"), index=True)
    canonical_name: Mapped[str] = mapped_column(String)
    emails_json: Mapped[str] = mapped_column(Text, default="[]")


class Ownership(Base):
    """Per-file per-author ownership derived from blame + recency (spec F4)."""

    __tablename__ = "ownership"

    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), primary_key=True)
    blame_share: Mapped[float] = mapped_column(Float, default=0.0)
    recent_share: Mapped[float] = mapped_column(Float, default=0.0)
    ownership: Mapped[float] = mapped_column(Float, default=0.0)
    last_commit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_ownership_file", "file_id"),
        Index("ix_ownership_author", "author_id"),
    )


class Commit(Base):
    """A commit from the repo's history."""

    __tablename__ = "commits"

    hash: Mapped[str] = mapped_column(String, primary_key=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repos.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id"), index=True, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime)
    message: Mapped[str] = mapped_column(Text)


class CommitFile(Base):
    """Files changed by a commit with added/deleted line counts."""

    __tablename__ = "commit_files"

    commit_hash: Mapped[str] = mapped_column(ForeignKey("commits.hash"), primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    added: Mapped[int] = mapped_column(Integer, default=0)
    deleted: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_commit_files_commit", "commit_hash"),
        Index("ix_commit_files_file", "file_id"),
    )


class Import(Base):
    """A resolved import edge: src imports dst."""

    __tablename__ = "imports"

    src_file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    dst_file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)

    __table_args__ = (
        Index("ix_imports_src", "src_file_id"),
        Index("ix_imports_dst", "dst_file_id"),
    )


class Coupling(Base):
    """Co-change coupling between two files (spec F3 step 3)."""

    __tablename__ = "coupling"

    file_a_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    file_b_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)
    co_changes: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (
        Index("ix_coupling_a", "file_a_id"),
        Index("ix_coupling_b", "file_b_id"),
    )


class Evidence(Base):
    """A raw source a decision was extracted from."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repos.id"), index=True)
    type: Mapped[str] = mapped_column(String)  # commit|pull_request|code_comment|doc|adr|manual
    ref: Mapped[str] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id"), index=True, nullable=True)

    __table_args__ = (UniqueConstraint("repo_id", "type", "ref", name="uq_evidence_repo_type_ref"),)


class Decision(Base):
    """A recorded reason behind a piece of code."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[str] = mapped_column(ForeignKey("repos.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text, default="")
    reasoning: Mapped[str] = mapped_column(Text, default="")
    alternatives: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String, default="low")  # high|medium|low
    created_at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String, default="extracted")  # extracted|manual
    skill_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    author: Mapped[str | None] = mapped_column(String, nullable=True)


class DecisionEvidence(Base):
    """Join table linking decisions to their evidence items."""

    __tablename__ = "decision_evidence"

    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), primary_key=True)
    evidence_id: Mapped[int] = mapped_column(ForeignKey("evidence.id"), primary_key=True)

    __table_args__ = (
        Index("ix_decision_evidence_decision", "decision_id"),
        Index("ix_decision_evidence_evidence", "evidence_id"),
    )


class DecisionFile(Base):
    """Join table linking decisions to the files they touch."""

    __tablename__ = "decision_files"

    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), primary_key=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), primary_key=True)

    __table_args__ = (
        Index("ix_decision_files_decision", "decision_id"),
        Index("ix_decision_files_file", "file_id"),
    )


class Job(Base):
    """A background job (ingestion) with progress reporting."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    repo_id: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String, default="ingest")
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|running|done|failed
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LLMCache(Base):
    """Cache of LLM responses keyed by a hash of prompt + input (spec §11)."""

    __tablename__ = "llm_cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    response: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime)


# Relationships used by query helpers (kept minimal and explicit).
Decision.evidence_links = relationship(DecisionEvidence, viewonly=True, lazy="selectin")
Decision.file_links = relationship(DecisionFile, viewonly=True, lazy="selectin")
