"""Onboarding trail generation (spec F7)."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import LLMError
from core.llm.prompts_loader import load_prompt
from core.llm.provider import LLMProvider, cached_complete_json
from core.models.db_models import Decision, DecisionFile, File, Import
from core.models.schemas import Trail, TrailStep
from core.search.index import tokenize
from core.services.queries import compact_decision

MIN_STEPS = 6
MAX_STEPS = 12
READ_SPEED_LPM = 40


def build_trail(
    session: Session,
    repo_id: str,
    topic: str | None = None,
    max_steps: int = 10,
    repo_path: Path | None = None,
    provider: LLMProvider | None = None,
) -> Trail:
    """Build an ordered reading path (topic-focused or general)."""
    max_steps = max(MIN_STEPS, min(max_steps, MAX_STEPS))
    files = {
        f.path: f
        for f in session.scalars(select(File).where(File.repo_id == repo_id))
        if f.language in ("python", "javascript", "typescript", "vue")
    }
    if not files:
        return Trail(topic=topic, steps=[])

    decision_text = _decision_text_by_file(session, repo_id)

    if topic:
        candidates = _topic_candidates(topic, files, decision_text, repo_path, limit=max_steps * 2)
    else:
        candidates = _general_candidates(files, limit=max_steps * 2)
    if not candidates:
        return Trail(topic=topic, steps=[])

    ordered = _topological_order(session, candidates, files)[:max_steps]

    steps: list[TrailStep] = []
    for path in ordered:
        row = files[path]
        decisions = _top_decisions(session, repo_id, row.id)
        reason = _step_reason(session, row, provider, len(steps) + 1, len(ordered))
        steps.append(
            TrailStep(
                path=path,
                reason=reason,
                decisions=decisions,
                reading_minutes=max(1, math.ceil(row.loc / READ_SPEED_LPM)),
            )
        )
    return Trail(topic=topic, steps=steps)


def _decision_text_by_file(session: Session, repo_id: str) -> dict[int, str]:
    """Concatenated decision text per file id, for topic matching."""
    rows = session.execute(
        select(DecisionFile.file_id, Decision.title, Decision.summary, Decision.reasoning)
        .join(Decision, Decision.id == DecisionFile.decision_id)
        .where(Decision.repo_id == repo_id)
    ).all()
    result: dict[int, str] = {}
    for fid, title, summary, reasoning in rows:
        result[fid] = result.get(fid, "") + f" {title} {summary or ''} {reasoning or ''}"
    return result


def _topic_candidates(
    topic: str,
    files: dict[str, File],
    decision_text: dict[int, str],
    repo_path: Path | None,
    limit: int,
) -> list[str]:
    """Rank files by BM25 keyword match on path, content and decision text.

    Files with zero relevance never enter the trail (acceptance criterion).
    """
    paths = list(files)
    corpus: list[list[str]] = []
    for path in paths:
        row = files[path]
        doc = path + " " + (decision_text.get(row.id, ""))
        if repo_path is not None:
            try:
                doc += " " + (repo_path / path).read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                pass
        corpus.append(tokenize(doc))
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(topic))
    ranked = [(p, s) for p, s in zip(paths, scores) if s > 0]
    ranked.sort(key=lambda pair: -pair[1])
    return [p for p, _ in ranked[:limit]]


def _general_candidates(files: dict[str, File], limit: int) -> list[str]:
    """General trail: entry points first, then highest fan-in files."""
    ranked = sorted(
        files.values(),
        key=lambda f: (not f.is_entry_point, -f.fan_in, -f.loc),
    )
    return [f.path for f in ranked[:limit]]


def _topological_order(
    session: Session, candidates: list[str], files: dict[str, File]
) -> list[str]:
    """Order candidates so a file comes after its dependencies within the set,
    breaking ties by fan-in (high first)."""
    candidate_set = set(candidates)
    id_to_path = {files[p].id: p for p in candidates if p in files}
    deps: dict[str, set[str]] = {p: set() for p in candidates}
    for edge in session.scalars(select(Import)):
        src, dst = id_to_path.get(edge.src_file_id), id_to_path.get(edge.dst_file_id)
        if src in candidate_set and dst in candidate_set and src != dst:
            deps[src].add(dst)  # src depends on dst -> read dst first

    ordered: list[str] = []
    remaining = dict(deps)
    while remaining:
        ready = [p for p, d in remaining.items() if not (d & set(remaining))]
        if not ready:  # cycle: fall back to fan-in order for the rest
            ready = list(remaining)
        ready.sort(key=lambda p: (-files[p].fan_in, candidates.index(p)))
        chosen = ready[0]
        ordered.append(chosen)
        del remaining[chosen]
    return ordered


def _top_decisions(session: Session, repo_id: str, file_id: int):
    """The 1-2 most important (newest, highest-confidence) decisions of a file."""
    rows = session.scalars(
        select(Decision)
        .join(DecisionFile, DecisionFile.decision_id == Decision.id)
        .where(DecisionFile.file_id == file_id)
        .order_by(Decision.created_at.desc())
    ).all()
    rows.sort(key=lambda d: {"high": 0, "medium": 1, "low": 2}.get(d.confidence, 3))
    return [compact_decision(session, d) for d in rows[:2]]


def _step_reason(
    session: Session, row: File, provider: LLMProvider | None, position: int, total: int
) -> str:
    """One sentence explaining why to read this file now (LLM or template)."""
    if provider is not None and provider.available:
        try:
            payload = json.dumps(
                {
                    "path": row.path,
                    "summary": row.summary or "",
                    "fan_in": row.fan_in,
                    "position": position,
                    "total": total,
                }
            )
            raw = cached_complete_json(provider, session, load_prompt("trail_step"), payload)
            reason = str(raw.get("reason", "")).strip()
            if reason:
                return reason[:300]
        except LLMError:
            pass
    symbol = _top_symbol(row)
    base = f"Imported by {row.fan_in} file{'s' if row.fan_in != 1 else ''}"
    if row.is_entry_point:
        base = "An entry point of the repo; " + base.lower()
    return f"{base}; defines {symbol}." if symbol else f"{base}."


def _top_symbol(row: File) -> str | None:
    """Best-effort top-level symbol name from the stored summary or path."""
    stem = re.sub(r"\.[^.]+$", "", row.path.split("/")[-1])
    return stem if stem and stem not in ("index", "__init__") else None
