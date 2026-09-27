"""Knowledge holders, alias merging and bus factor (spec F4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

RECENT_WINDOW_DAYS = 365
INACTIVE_DAYS = 180
BLAME_WEIGHT = 0.7
RECENT_WEIGHT = 0.3
BUS_FACTOR_THRESHOLD = 0.5


@dataclass
class AuthorIdentity:
    """A canonical author with all merged (name, email) aliases."""

    canonical_name: str
    emails: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)


def merge_identities(
    raw_identities: list[tuple[str, str]],
    alias_overrides: dict[str, str] | None = None,
) -> dict[tuple[str, str], AuthorIdentity]:
    """Merge author identities that share an email, or share a name (spec F4.3).

    ``alias_overrides`` maps an email or name to a canonical name, loaded from
    ``.heirloom/authors.yml`` so users can correct mistakes.

    Returns a map from every raw (name, email) pair to its merged identity.
    """
    overrides = alias_overrides or {}
    # Union-find over raw pairs.
    parent: dict[tuple[str, str], tuple[str, str]] = {}

    def find(x: tuple[str, str]) -> tuple[str, str]:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: tuple[str, str], b: tuple[str, str]) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    pairs = sorted(set(raw_identities))
    for p in pairs:
        parent[p] = p

    by_email: dict[str, tuple[str, str]] = {}
    by_name: dict[str, tuple[str, str]] = {}
    for p in pairs:
        name, email = p
        email_key = email.strip().lower()
        name_key = name.strip().lower()
        if email_key:
            if email_key in by_email:
                union(by_email[email_key], p)
            else:
                by_email[email_key] = p
        if name_key:
            if name_key in by_name:
                union(by_name[name_key], p)
            else:
                by_name[name_key] = p

    groups: dict[tuple[str, str], AuthorIdentity] = {}
    result: dict[tuple[str, str], AuthorIdentity] = {}
    for p in pairs:
        root = find(p)
        if root not in groups:
            groups[root] = AuthorIdentity(canonical_name=root[0])
        identity = groups[root]
        identity.names.add(p[0])
        if p[1]:
            identity.emails.add(p[1])
        result[p] = identity

    # Apply user overrides from authors.yml (email or name -> canonical name).
    for identity in groups.values():
        for email in identity.emails:
            if email.lower() in overrides:
                identity.canonical_name = overrides[email.lower()]
        for name in identity.names:
            if name.lower() in overrides:
                identity.canonical_name = overrides[name.lower()]

    return result


@dataclass
class OwnershipShare:
    """Final ownership of one author over one file."""

    author: str
    blame_share: float
    recent_share: float
    ownership: float
    last_commit_at: datetime | None


def compute_ownership(
    blame_lines: dict[str, int],
    recent_lines: dict[str, int],
    last_commit: dict[str, datetime],
) -> list[OwnershipShare]:
    """Combine blame and recency into final ownership (spec F4.2).

    ``blame_lines``: author -> surviving lines from blame.
    ``recent_lines``: author -> lines changed in the last 12 months.
    Final ownership = 0.7 * blame_share + 0.3 * recent_share. When there is
    no recent activity at all, blame share alone is used.
    """
    total_blame = sum(blame_lines.values())
    total_recent = sum(recent_lines.values())
    authors = set(blame_lines) | set(recent_lines)

    shares: list[OwnershipShare] = []
    for author in authors:
        blame_share = blame_lines.get(author, 0) / total_blame if total_blame else 0.0
        recent_share = recent_lines.get(author, 0) / total_recent if total_recent else 0.0
        if total_recent:
            ownership = BLAME_WEIGHT * blame_share + RECENT_WEIGHT * recent_share
        else:
            ownership = blame_share
        shares.append(
            OwnershipShare(
                author=author,
                blame_share=round(blame_share, 4),
                recent_share=round(recent_share, 4),
                ownership=round(ownership, 4),
                last_commit_at=last_commit.get(author),
            )
        )
    shares.sort(key=lambda s: (-s.ownership, s.author))
    return shares


def bus_factor(shares: list[OwnershipShare]) -> int:
    """Smallest number of authors whose ownership sums to >= 50% (spec F4.4).

    An empty file (no owners) gets bus factor 0.
    """
    total = sum(s.ownership for s in shares)
    if total <= 0:
        return 0
    cumulative = 0.0
    for count, share in enumerate(sorted(shares, key=lambda s: -s.ownership), start=1):
        cumulative += share.ownership / total
        if cumulative >= BUS_FACTOR_THRESHOLD - 1e-9:
            return count
    return len(shares)


def is_at_risk(shares: list[OwnershipShare], factor: int, now: datetime | None = None) -> bool:
    """At risk = bus factor 1 and top owner inactive for 180+ days (spec F4.5)."""
    if factor != 1 or not shares:
        return False
    top = shares[0]
    if top.last_commit_at is None:
        return True  # unknown activity for the single owner counts as risk
    now = now or datetime.utcnow()
    return (now - top.last_commit_at) > timedelta(days=INACTIVE_DAYS)


def is_inactive(last_commit_at: datetime | None, now: datetime | None = None) -> bool:
    """Whether an author counts as inactive (no commit in 180 days)."""
    if last_commit_at is None:
        return True
    now = now or datetime.utcnow()
    return (now - last_commit_at) > timedelta(days=INACTIVE_DAYS)
