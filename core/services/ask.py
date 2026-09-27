"""Ask Heirloom: question routing and cited answers (spec F8)."""

from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import FileNotFoundInRepoError, LLMError
from core.llm.prompts_loader import load_prompt
from core.llm.provider import LLMProvider, cached_complete_json
from core.models.db_models import Decision, File
from core.models.schemas import AskAnswer
from core.search.index import DecisionIndex
from core.services.queries import holders_for_file, impact_for_file

NO_ANSWER = "Heirloom has no recorded reasoning for this"


def route_question(question: str) -> str:
    """Rule-based routing: who -> holders, impact -> F3, else decision search."""
    q = question.lower()
    if re.search(r"\bwho\b", q):
        return "who"
    if "what breaks" in q or "impact" in q or "affected" in q:
        return "impact"
    return "decisions"


def _find_file_in_question(session: Session, repo_id: str, question: str) -> str | None:
    """Match a repo file path mentioned in the question, longest match first."""
    paths = list(session.scalars(select(File.path).where(File.repo_id == repo_id)))
    q = question.lower()
    candidates = [p for p in paths if p.lower() in q or p.split("/")[-1].lower() in q]
    candidates.sort(key=len, reverse=True)
    return candidates[0] if candidates else None


def ask(
    session: Session,
    repo_id: str,
    question: str,
    provider: LLMProvider,
) -> AskAnswer:
    """Answer a question about the repo with citations (spec F8)."""
    route = route_question(question)

    if route == "who":
        path = _find_file_in_question(session, repo_id, question)
        if path:
            try:
                file_row = session.scalar(
                    select(File).where(File.repo_id == repo_id, File.path == path)
                )
                holders = holders_for_file(session, file_row)
                if holders:
                    parts = [
                        f"{h.name} ({h.ownership:.0%}{', inactive' if h.inactive else ''})"
                        for h in holders
                    ]
                    return AskAnswer(
                        answer=f"Knowledge holders for {path}: " + ", ".join(parts), route="who"
                    )
            except FileNotFoundInRepoError:
                pass
        return AskAnswer(
            answer=f"{NO_ANSWER}. Try `who <file>` with an exact repo path.", route="who"
        )

    if route == "impact":
        path = _find_file_in_question(session, repo_id, question)
        if path:
            try:
                impact = impact_for_file(session, repo_id, path, limit=10)
            except FileNotFoundInRepoError:
                impact = []
            if impact:
                parts = [f"{i.path} ({i.reason})" for i in impact[:5]]
                return AskAnswer(
                    answer=f"If {path} changes, check: " + "; ".join(parts), route="impact"
                )
        return AskAnswer(
            answer=f"{NO_ANSWER}. Name a specific file to get its impact set.", route="impact"
        )

    # Decision search route.
    index = DecisionIndex(session, repo_id)
    hits = index.search(question, limit=8)
    if not hits:
        suggestion = _find_file_in_question(session, repo_id, question)
        extra = f" The closest file is '{suggestion}' — open its Why Card." if suggestion else ""
        return AskAnswer(answer=f"{NO_ANSWER}.{extra}", route="none")

    decisions = [session.get(Decision, h.decision_id) for h in hits]

    if provider.available:
        payload = json.dumps(
            {
                "question": question,
                "decisions": [
                    {
                        "id": str(d.id),
                        "title": d.title,
                        "summary": d.summary,
                        "reasoning": d.reasoning,
                    }
                    for d in decisions
                ],
            },
            ensure_ascii=False,
        )
        try:
            raw = cached_complete_json(provider, session, load_prompt("ask_citations"), payload)
            answer = str(raw.get("answer", "")).strip()
            citations = [
                str(c) for c in raw.get("citations", []) if str(c) in {str(d.id) for d in decisions}
            ]
            if answer:
                # Enforcement: strip claims with no valid citation set at all.
                if not citations and NO_ANSWER not in answer:
                    answer = f"{NO_ANSWER}."
                return AskAnswer(answer=answer, citations=citations, route="decisions")
        except LLMError:
            pass

    # Deterministic fallback: ranked decision list, honestly labeled.
    top = decisions[:5]
    lines = [
        f"[{d.id}] {d.title}" + (f" — {d.reasoning[:120]}" if d.reasoning else "") for d in top
    ]
    return AskAnswer(
        answer="LLM not configured, showing matching decisions:\n" + "\n".join(lines),
        citations=[str(d.id) for d in top],
        route="decisions",
    )
