"""Deterministic fixture repo generator (spec §15).

Builds a small git repository with scripted commits, multiple authors (with
aliases), imports across Python and TypeScript, intent comments, and an ADR,
so all core tests run against known-good data.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path

ALICE = ("Alice Chen", "alice@example.com")
ALICE_ALIAS = ("Alice C", "alice@example.com")  # same email -> merged
BOB = ("Bob Singh", "bob@example.com")
CHARLIE = ("Charlie Fox", "charlie@personal.example.com")
CHARLIE_WORK = ("Charlie Fox", "charlie@work.example.com")  # same name -> merged

# Relative to today so "recent" vs "inactive" never drifts as real time passes.
NOW = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)


def _run(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, author: tuple[str, str], message: str, when: datetime) -> None:
    stamp = when.strftime("%Y-%m-%dT%H:%M:%S")
    subprocess.run(
        [
            "git",
            "-c",
            f"user.name={author[0]}",
            "-c",
            f"user.email={author[1]}",
            "commit",
            "-m",
            message,
            "--no-gpg-sign",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            **__import__("os").environ,
            "GIT_AUTHOR_DATE": stamp,
            "GIT_COMMITTER_DATE": stamp,
            "GIT_AUTHOR_NAME": author[0],
            "GIT_AUTHOR_EMAIL": author[1],
            "GIT_COMMITTER_NAME": author[0],
            "GIT_COMMITTER_EMAIL": author[1],
        },
    )


def _write(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))  # LF on every OS -> stable commit hashes
    _run(repo, "add", rel)


def make_fixture_repo(target: Path) -> Path:
    """Create the fixture repo at ``target`` and return its path."""
    target.mkdir(parents=True, exist_ok=True)
    _run(target, "init", "-b", "main")

    # --- Day -700: Bob writes the legacy module he alone understands -------
    _write(
        target,
        "src/legacy.py",
        '"""Legacy billing reconciliation."""\n\n'
        + "\n".join(f"def step_{i}():\n    return {i}\n" for i in range(20)),
    )
    _commit(target, BOB, "Add legacy billing reconciliation module", NOW - timedelta(days=700))

    # --- Day -400: Alice builds the app core ---------------------------------
    _write(
        target,
        "src/utils.py",
        '"""Date and string helpers."""\n\n\ndef fmt(x):\n    return str(x)\n',
    )
    _write(
        target,
        "src/app.py",
        '"""Application entry point."""\nfrom src import utils\nfrom src.auth import session\n\n\ndef main():\n    return utils.fmt(session.get())\n',
    )
    _write(
        target,
        "src/auth/session.py",
        '"""Session storage."""\n# DO NOT switch to in-memory sessions: multi-worker deploys need shared state\nimport json\n\n\ndef get():\n    # NOTE: we use Redis because sessions must survive restarts\n    return json.dumps({})\n',
    )
    _write(target, "src/auth/__init__.py", "")
    _write(target, "src/__init__.py", "")
    _commit(
        target,
        ALICE,
        "Use Redis for session storage because sessions must survive restarts\n\n"
        "We evaluated in-memory storage instead of Redis but multi-worker deployments "
        "need shared state, so that sessions survive process restarts.",
        NOW - timedelta(days=400),
    )

    # --- Web layer by Charlie (two emails) -----------------------------------
    _write(
        target,
        "web/helpers.ts",
        "/** Shared web helpers. */\nexport function fmtDate(d: Date): string {\n  return d.toISOString();\n}\n",
    )
    _write(
        target,
        "web/index.ts",
        "/** Web entry point. */\nimport { fmtDate } from './helpers';\n\nconsole.log(fmtDate(new Date()));\n",
    )
    _commit(target, CHARLIE, "Add web entry point and helpers", NOW - timedelta(days=300))

    _write(
        target,
        "web/helpers.ts",
        "/** Shared web helpers. */\nexport function fmtDate(d: Date): string {\n  // HACK: slice off ms because the legacy API rejects fractional seconds\n  return d.toISOString().slice(0, 19);\n}\n",
    )
    _commit(
        target,
        CHARLIE_WORK,
        "Truncate ISO dates because the legacy API rejects fractional seconds",
        NOW - timedelta(days=250),
    )

    # --- Co-change pattern: app.py + utils.py together 4 times ---------------
    for i in range(4):
        _write(
            target,
            "src/utils.py",
            f'"""Date and string helpers."""\n\n\ndef fmt(x):\n    return str(x)  # rev {i}\n',
        )
        _write(
            target,
            "src/app.py",
            f'"""Application entry point."""\nfrom src import utils\nfrom src.auth import session\n\n\ndef main():\n    return utils.fmt(session.get())  # rev {i}\n',
        )
        author = ALICE if i % 2 == 0 else ALICE_ALIAS
        _commit(
            target,
            author,
            f"perf: tune formatting pipeline pass {i}",
            NOW - timedelta(days=200 - i * 10),
        )

    # --- ADR ------------------------------------------------------------------
    _write(
        target,
        "docs/adr/0001-use-sqlite.md",
        "# 1. Use SQLite for local storage\n\n## Status\nAccepted\n\n## Context\n"
        "We need zero-setup local persistence.\n\n## Decision\nUse SQLite because it "
        "requires no server and ships with Python.\n\n## Consequences\nSingle-writer only.\n",
    )
    _write(target, "README.md", "# Fixture Project\n\nA tiny project used by Heirloom's tests.\n")
    _commit(target, ALICE, "docs: add ADR for SQLite and README", NOW - timedelta(days=180))

    # --- Recent work by Alice keeps her active --------------------------------
    _write(
        target,
        "src/utils.py",
        '"""Date and string helpers."""\n\n\ndef fmt(x):\n    return format(x)\n\n\ndef parse(x):\n    return x.strip()\n',
    )
    _commit(
        target,
        ALICE,
        "Replace str() with format() in fmt so that custom formatters work\n\n"
        "This is a workaround because str() ignores __format__ hooks.",
        NOW - timedelta(days=20),
    )

    return target


if __name__ == "__main__":
    import sys

    make_fixture_repo(Path(sys.argv[1] if len(sys.argv) > 1 else "fixture_repo"))
