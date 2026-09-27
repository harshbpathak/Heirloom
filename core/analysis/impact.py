"""Impact set computation (spec F3 step 4).

Impact of changing file F = importers of F (direct and 2-hop) plus files
strongly co-changed with F, ranked by 0.6 * import_proximity + 0.4 * coupling.
"""

from __future__ import annotations

from dataclasses import dataclass

IMPORT_WEIGHT = 0.6
COUPLING_WEIGHT = 0.4
DIRECT_PROXIMITY = 1.0
TWO_HOP_PROXIMITY = 0.5
MAX_RESULTS = 20


@dataclass
class ImpactEntry:
    """One impacted file with its score and a human-readable reason."""

    path: str
    score: float
    reason: str


def compute_impact(
    target: str,
    importers: dict[str, set[str]],
    coupling: dict[tuple[str, str], tuple[int, float]],
    changes: dict[str, int] | None = None,
    limit: int = 10,
) -> list[ImpactEntry]:
    """Rank the files likely affected if ``target`` changes.

    ``importers`` maps a file to the set of files importing it.
    ``coupling`` maps an (a, b) sorted pair to (co_changes, score).
    ``changes`` maps a file to its total change count (for reason strings).
    """
    proximity: dict[str, float] = {}
    direct = importers.get(target, set())
    for f in direct:
        proximity[f] = DIRECT_PROXIMITY
    for f in direct:
        for g in importers.get(f, set()):
            if g != target and g not in proximity:
                proximity[g] = TWO_HOP_PROXIMITY

    coupled: dict[str, tuple[int, float]] = {}
    for (a, b), (co, score) in coupling.items():
        other = b if a == target else a if b == target else None
        if other is not None and other != target:
            coupled[other] = (co, score)

    entries: list[ImpactEntry] = []
    for path in set(proximity) | set(coupled):
        prox = proximity.get(path, 0.0)
        co, coup_score = coupled.get(path, (0, 0.0))
        combined = IMPORT_WEIGHT * prox + COUPLING_WEIGHT * coup_score
        reasons: list[str] = []
        if prox == DIRECT_PROXIMITY:
            reasons.append("imports this file directly")
        elif prox == TWO_HOP_PROXIMITY:
            reasons.append("imports this file through one intermediate file")
        if co:
            total = min(changes.get(path, co), changes.get(target, co)) if changes else co
            reasons.append(f"changed together in {co} of {max(total, co)} commits")
        entries.append(ImpactEntry(path=path, score=round(combined, 4), reason="; ".join(reasons)))

    entries.sort(key=lambda e: (-e.score, e.path))
    return entries[: min(limit, MAX_RESULTS)]
