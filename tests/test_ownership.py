"""Tests for ownership, alias merging and bus factor (spec F4)."""

from datetime import datetime, timedelta

from core.analysis.ownership import (
    bus_factor,
    compute_ownership,
    is_at_risk,
    merge_identities,
)

NOW = datetime(2026, 9, 27)


def test_blame_share_only_when_no_recent_activity():
    shares = compute_ownership({"alice": 70, "bob": 30}, {}, {})
    by = {s.author: s for s in shares}
    assert by["alice"].ownership == 0.7
    assert by["bob"].ownership == 0.3


def test_recency_weighting():
    shares = compute_ownership({"alice": 100}, {"bob": 50}, {})
    by = {s.author: s for s in shares}
    # alice: 0.7*1.0 + 0.3*0 = 0.7; bob: 0.7*0 + 0.3*1.0 = 0.3
    assert by["alice"].ownership == 0.7
    assert by["bob"].ownership == 0.3


def test_merge_identities_by_email():
    merged = merge_identities([("Alice Chen", "a@x.com"), ("Alice C", "a@x.com")])
    assert merged[("Alice Chen", "a@x.com")] is merged[("Alice C", "a@x.com")]


def test_merge_identities_by_name_different_emails():
    merged = merge_identities([("Charlie Fox", "c@a.com"), ("Charlie Fox", "c@b.com")])
    identity = merged[("Charlie Fox", "c@a.com")]
    assert identity is merged[("Charlie Fox", "c@b.com")]
    assert identity.emails == {"c@a.com", "c@b.com"}


def test_alias_overrides_from_authors_yml():
    merged = merge_identities([("A. Chen", "a@x.com")], {"a@x.com": "Alice Chen"})
    assert merged[("A. Chen", "a@x.com")].canonical_name == "Alice Chen"


def test_bus_factor_single_author():
    shares = compute_ownership({"alice": 100}, {}, {})
    assert bus_factor(shares) == 1


def test_bus_factor_even_split():
    shares = compute_ownership({"a": 25, "b": 25, "c": 25, "d": 25}, {}, {})
    assert bus_factor(shares) == 2  # two authors reach exactly 50%


def test_bus_factor_empty_file():
    assert bus_factor([]) == 0


def test_at_risk_requires_inactive_single_owner():
    recent = {"alice": NOW - timedelta(days=10)}
    old = {"alice": NOW - timedelta(days=300)}
    active = compute_ownership({"alice": 100}, {}, recent)
    stale = compute_ownership({"alice": 100}, {}, old)
    assert not is_at_risk(active, 1, NOW)
    assert is_at_risk(stale, 1, NOW)


def test_at_risk_never_for_bus_factor_2():
    shares = compute_ownership({"a": 50, "b": 50}, {}, {})
    assert not is_at_risk(shares, 2, NOW)


def test_canonical_name_is_most_used_alias():
    raw = [("Alice Chen", "a@x.com")] * 5 + [("Alice C", "a@x.com")] * 2
    merged = merge_identities(raw)
    assert merged[("Alice C", "a@x.com")].canonical_name == "Alice Chen"


def test_at_risk_uses_repo_wide_activity_not_file_activity():
    # Alice last touched THIS file 300 days ago but committed elsewhere 10 days ago.
    shares = compute_ownership({"alice": 100}, {}, {"alice": NOW - timedelta(days=300)})
    assert is_at_risk(shares, 1, NOW)  # file-level fallback alone would say at risk
    assert not is_at_risk(shares, 1, NOW, {"alice": NOW - timedelta(days=10)})
