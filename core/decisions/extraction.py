"""Decision extraction from evidence: candidate filter, heuristic and LLM paths (spec F2)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from core.errors import LLMError
from core.llm.prompts_loader import load_prompt
from core.llm.provider import LLMProvider, cached_complete_json
from core.models.schemas import ExtractionResult

CANDIDATE_KEYWORDS = (
    "because", "instead", "so that", "revert", "workaround", "migrate",
    "replace", "deprecate", "fix race", "perf",
)
REASONING_MARKERS = ("because", "so that", "instead of", "to avoid")
MIN_COMMIT_LENGTH = 60
MIN_PR_BODY_LENGTH = 100
MAX_TITLE = 80
LLM_BATCH_SIZE = 10


@dataclass
class EvidenceCandidate:
    """One evidence item that may yield a decision."""

    type: str  # commit|pull_request|code_comment|adr
    ref: str
    text: str
    url: str | None = None
    date: datetime | None = None
    files: list[str] = field(default_factory=list)


@dataclass
class DraftDecision:
    """An extracted decision before persistence."""

    title: str
    summary: str
    reasoning: str
    alternatives: str | None
    confidence: str  # high|medium|low
    files: list[str]
    evidence_refs: list[str]  # "type:ref" keys
    created_at: datetime | None = None


def is_candidate(item: EvidenceCandidate) -> bool:
    """Apply the candidate filter from spec F2 step 1."""
    if item.type in ("code_comment", "adr"):
        return True
    text_lower = item.text.lower()
    if item.type == "commit":
        if len(item.text.strip()) > MIN_COMMIT_LENGTH:
            return True
        return any(kw in text_lower for kw in CANDIDATE_KEYWORDS)
    if item.type == "pull_request":
        # Body length excludes the title line.
        body = item.text.split("\n", 1)[1] if "\n" in item.text else ""
        return len(body.strip()) > MIN_PR_BODY_LENGTH
    return False


_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    """Naive sentence split on punctuation boundaries."""
    flat = " ".join(text.split())
    return [s.strip() for s in _SENTENCE_RE.split(flat) if s.strip()]


def heuristic_extract(item: EvidenceCandidate) -> DraftDecision | None:
    """Deterministic extraction used when no LLM is configured (spec F2 step 3).

    Title = first line (max 80 chars). Summary = first 2 sentences.
    Reasoning = sentences containing because/so that/instead of/to avoid.
    Confidence: high for ADRs (spec F2 acceptance), low otherwise.
    """
    text = item.text.strip()
    if not text:
        return None
    first_line = text.split("\n", 1)[0].strip()
    title = first_line[:MAX_TITLE] if first_line else text[:MAX_TITLE]
    body = text[len(first_line):].strip() or text
    sentences = _sentences(body)
    summary = " ".join(sentences[:2])[:500]
    reasoning_sentences = [
        s for s in _sentences(text) if any(marker in s.lower() for marker in REASONING_MARKERS)
    ]
    reasoning = " ".join(reasoning_sentences)[:1000]
    if item.type in ("commit", "pull_request") and not reasoning and len(text) <= MIN_COMMIT_LENGTH:
        return None
    confidence = "high" if item.type == "adr" else "low"
    return DraftDecision(
        title=title,
        summary=summary,
        reasoning=reasoning,
        alternatives=None,
        confidence=confidence,
        files=list(item.files),
        evidence_refs=[f"{item.type}:{item.ref}"],
        created_at=item.date,
    )


def llm_extract(
    provider: LLMProvider,
    session: Any,
    candidates: list[EvidenceCandidate],
) -> tuple[list[DraftDecision], list[str]]:
    """LLM extraction in batches of up to 10 candidates (spec F2 step 2).

    Returns (decisions, dropped_refs). Invalid model output is dropped and
    reported, never silently kept. Falls back per-batch to heuristics when
    the provider call itself fails.
    """
    prompt = load_prompt("decision_extraction")
    decisions: list[DraftDecision] = []
    dropped: list[str] = []
    by_ref = {f"{c.type}:{c.ref}": c for c in candidates}

    for start in range(0, len(candidates), LLM_BATCH_SIZE):
        batch = candidates[start : start + LLM_BATCH_SIZE]
        payload = _batch_payload(batch)
        try:
            raw = cached_complete_json(provider, session, prompt, payload)
            parsed = ExtractionResult.model_validate(raw)
        except (LLMError, ValidationError):
            # Whole-batch failure: heuristics keep the pipeline moving.
            for item in batch:
                draft = heuristic_extract(item)
                if draft:
                    decisions.append(draft)
            continue
        for extracted in parsed.decisions:
            refs = [r for r in extracted.evidence_refs if r in by_ref]
            if not refs:
                dropped.append(extracted.title)
                continue
            source = by_ref[refs[0]]
            confidence = "high" if source.type == "adr" else "medium"
            files = extracted.files or list(source.files)
            decisions.append(
                DraftDecision(
                    title=extracted.title[:MAX_TITLE],
                    summary=extracted.summary[:500],
                    reasoning=extracted.reasoning[:2000],
                    alternatives=extracted.alternatives,
                    confidence=confidence,
                    files=files,
                    evidence_refs=refs,
                    created_at=source.date,
                )
            )
    return decisions, dropped


def _batch_payload(batch: list[EvidenceCandidate]) -> str:
    """Serialize a batch of candidates for the extraction prompt."""
    import json

    return json.dumps(
        [
            {
                "evidence_ref": f"{c.type}:{c.ref}",
                "type": c.type,
                "text": c.text[:3000],
                "files": c.files[:20],
            }
            for c in batch
        ],
        ensure_ascii=False,
    )


def extract_decisions(
    candidates: list[EvidenceCandidate],
    provider: LLMProvider,
    session: Any = None,
) -> list[DraftDecision]:
    """Extract decisions from candidates using the best available path."""
    eligible = [c for c in candidates if is_candidate(c)]
    if provider.available and session is not None:
        decisions, _ = llm_extract(provider, session, eligible)
        return decisions
    results = []
    for item in eligible:
        draft = heuristic_extract(item)
        if draft:
            results.append(draft)
    return results
