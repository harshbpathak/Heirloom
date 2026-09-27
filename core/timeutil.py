"""Naive-UTC timestamp helper (SQLite stores naive datetimes)."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current UTC time as a naive datetime (what our SQLite columns store)."""
    return datetime.now(UTC).replace(tzinfo=None)
