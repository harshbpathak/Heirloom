"""Near-duplicate merging of decisions (spec F2 step 5).

Two decisions touching the same files with title similarity above 0.85
(rapidfuzz ratio) merge into one decision carrying both evidence items.
"""

from __future__ import annotations

from rapidfuzz import fuzz

from core.decisions.extraction import DraftDecision

SIMILARITY_THRESHOLD = 0.85


def _similar(a: DraftDecision, b: DraftDecision) -> bool:
    """Same-file overlap plus high title similarity."""
    if not (set(a.files) & set(b.files)):
        return False
    return fuzz.ratio(a.title.lower(), b.title.lower()) / 100.0 > SIMILARITY_THRESHOLD


_CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


def merge_decisions(decisions: list[DraftDecision]) -> list[DraftDecision]:
    """Merge near-duplicates, keeping the higher-confidence draft as the base."""
    merged: list[DraftDecision] = []
    for draft in decisions:
        target = next((m for m in merged if _similar(m, draft)), None)
        if target is None:
            merged.append(draft)
            continue
        # Keep the stronger draft's text; union files and evidence.
        keep, absorb = (target, draft)
        if _CONFIDENCE_RANK.get(draft.confidence, 0) > _CONFIDENCE_RANK.get(target.confidence, 0):
            keep, absorb = (draft, target)
            merged[merged.index(target)] = keep
        keep.files = sorted(set(keep.files) | set(absorb.files))
        keep.evidence_refs = sorted(set(keep.evidence_refs) | set(absorb.evidence_refs))
        if not keep.reasoning and absorb.reasoning:
            keep.reasoning = absorb.reasoning
        if not keep.alternatives and absorb.alternatives:
            keep.alternatives = absorb.alternatives
    return merged
