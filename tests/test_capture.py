"""Tests for decision-record Markdown round-trip (spec F9, §10.4)."""

from datetime import date

from core.decisions.capture import (
    DecisionRecord,
    load_decision_records,
    next_record_id,
    parse_decision_record,
    write_decision_record,
)


def _record(id="0001", title="Use Redis for session storage"):
    return DecisionRecord(
        id=id,
        title=title,
        date=date(2026, 9, 27),
        files=["src/auth/session.py"],
        confidence="high",
        source="manual",
        author="Jane Doe",
        skill_hash=None,
        context="Sessions were lost on restart.",
        decision="Use Redis.",
        reasoning="Sessions must survive restarts.",
        alternatives="In-memory storage was rejected: not shared across workers.",
    )


def test_write_and_parse_round_trip(tmp_path):
    path = write_decision_record(tmp_path, _record())
    assert path.name == "0001-use-redis-for-session-storage.md"
    parsed = parse_decision_record(path.read_text(encoding="utf-8"))
    assert parsed.title == "Use Redis for session storage"
    assert parsed.files == ["src/auth/session.py"]
    assert parsed.reasoning == "Sessions must survive restarts."
    assert parsed.author == "Jane Doe"
    assert parsed.date == date(2026, 9, 27)


def test_next_record_id_increments(tmp_path):
    assert next_record_id(tmp_path) == "0001"
    write_decision_record(tmp_path, _record())
    assert next_record_id(tmp_path) == "0002"
    write_decision_record(tmp_path, _record(id="0002", title="Second decision"))
    assert next_record_id(tmp_path) == "0003"


def test_load_decision_records(tmp_path):
    write_decision_record(tmp_path, _record())
    records = load_decision_records(tmp_path)
    assert len(records) == 1
    rel_path, record = records[0]
    assert rel_path.startswith(".heirloom/decisions/")
    assert record.title == "Use Redis for session storage"


def test_parse_rejects_no_front_matter():
    assert parse_decision_record("# just markdown\n\nno yaml here") is None
