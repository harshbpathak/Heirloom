"""Co-change coupling from the commit log (spec F3 step 3).

Coupling score = co_changes(A, B) / min(changes(A), changes(B)).
Pairs are kept when co_changes >= 3 and score >= 0.3. Commits touching
more than 30 files are ignored (bulk moves and reformats carry no signal).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations

MAX_FILES_PER_COMMIT = 30
MIN_CO_CHANGES = 3
MIN_SCORE = 0.3


@dataclass(frozen=True)
class CouplingPair:
    """A surviving co-change pair; file_a < file_b lexicographically."""

    file_a: str
    file_b: str
    co_changes: int
    score: float


def compute_coupling(commit_files: list[list[str]]) -> list[CouplingPair]:
    """Compute coupling pairs from a list of per-commit changed-file lists."""
    change_counts: Counter[str] = Counter()
    pair_counts: defaultdict[tuple[str, str], int] = defaultdict(int)

    for files in commit_files:
        unique = sorted(set(files))
        if not unique or len(unique) > MAX_FILES_PER_COMMIT:
            continue
        for path in unique:
            change_counts[path] += 1
        for a, b in combinations(unique, 2):
            pair_counts[(a, b)] += 1

    results: list[CouplingPair] = []
    for (a, b), co in pair_counts.items():
        if co < MIN_CO_CHANGES:
            continue
        denom = min(change_counts[a], change_counts[b])
        if denom == 0:
            continue
        score = co / denom
        if score >= MIN_SCORE:
            results.append(CouplingPair(file_a=a, file_b=b, co_changes=co, score=round(score, 4)))
    results.sort(key=lambda p: (-p.score, -p.co_changes, p.file_a, p.file_b))
    return results
