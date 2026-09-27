"""BM25 search over decisions (spec F2/F8) using rank_bm25."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.db_models import Decision, DecisionEvidence, Evidence

_TOKEN_RE = re.compile(r"[a-z0-9]+")

MIN_SCORE = 0.1


def tokenize(text: str) -> list[str]:
    """Lower-case alphanumeric tokenizer (also splits paths and identifiers)."""
    return _TOKEN_RE.findall(text.lower().replace("_", " ").replace("-", " ").replace("/", " "))


@dataclass
class SearchHit:
    """One decision returned by search."""

    decision_id: int
    score: float


class DecisionIndex:
    """An in-memory BM25 index over a repo's decisions."""

    def __init__(self, session: Session, repo_id: str) -> None:
        self._ids: list[int] = []
        corpus: list[list[str]] = []
        decisions = session.scalars(select(Decision).where(Decision.repo_id == repo_id)).all()
        for d in decisions:
            evidence_text = " ".join(
                e.text[:500]
                for e in session.scalars(
                    select(Evidence)
                    .join(DecisionEvidence, DecisionEvidence.evidence_id == Evidence.id)
                    .where(DecisionEvidence.decision_id == d.id)
                )
            )
            doc = " ".join([d.title, d.summary or "", d.reasoning or "", evidence_text])
            self._ids.append(d.id)
            corpus.append(tokenize(doc))
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def search(self, query: str, limit: int = 8) -> list[SearchHit]:
        """Top decisions for a query; empty when nothing scores above threshold."""
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(zip(self._ids, scores), key=lambda pair: -pair[1])
        return [
            SearchHit(decision_id=i, score=round(float(s), 4))
            for i, s in ranked[:limit]
            if s > MIN_SCORE
        ]
