"""Build demo snapshots for the three chosen public repos (spec F11).

Run with:
    HEIRLOOM_HOME=demo python scripts/build_demo_snapshots.py

Ingests each repo with --max-commits 2000, prints ingest timing (the spec's
"2000 commits in under 3 minutes" check), then pre-builds Why Cards for every
analysed file while the clone still exists so that summaries are stored in
files.summary and warnings are available offline.
"""

from __future__ import annotations

import os
import time

# Ensure HEIRLOOM_HOME is set before any core imports touch Settings.
if "HEIRLOOM_HOME" not in os.environ:
    os.environ["HEIRLOOM_HOME"] = "demo"

from sqlalchemy import select

from core.config import get_settings
from core.db import session_for
from core.ingest.pipeline import ingest_repo, resolve_source
from core.llm.provider import get_provider
from core.models.db_models import File
from core.services.whycard import build_why_card

# Three repos chosen for the demo:
#   pallets/click   – Python, ~2 000 meaningful commits, well-known, medium size
#   expressjs/express – JavaScript, large commit history, very recognisable
#   sindresorhus/ky – TypeScript, small focused codebase, contrasts the others
DEMO_REPOS = [
    "https://github.com/pallets/click",
    "https://github.com/expressjs/express",
    "https://github.com/sindresorhus/ky",
]

MAX_COMMITS = 2000


def _progress(pct: int, msg: str) -> None:
    print(f"  [{pct:3d}%] {msg}", flush=True)


def main() -> None:
    settings = get_settings()
    print(f"HEIRLOOM_HOME = {settings.heirloom_home}")
    print(f"DB dir        = {settings.db_dir}")
    print()

    provider = get_provider(settings)

    for source in DEMO_REPOS:
        print(f"=== {source} ===")
        t0 = time.perf_counter()
        repo_id = ingest_repo(
            source,
            max_commits=MAX_COMMITS,
            settings=settings,
            progress=_progress,
        )
        ingest_secs = time.perf_counter() - t0
        print(f"  ingest done in {ingest_secs:.1f}s  (limit: 180s)")
        if ingest_secs > 180:
            print("  WARNING: exceeded 3-minute target")

        # Pre-build Why Cards while the clone still exists.
        repo_path = resolve_source(source, settings, MAX_COMMITS)
        print("  Pre-building Why Cards…", flush=True)
        t1 = time.perf_counter()
        built = 0
        errors = 0
        with session_for(repo_id, settings.db_dir) as session:
            paths = [
                f.path
                for f in session.scalars(select(File).where(File.repo_id == repo_id))
            ]
        # Each Why Card call gets its own session so failures are isolated.
        for path in paths:
            try:
                with session_for(repo_id, settings.db_dir) as session:
                    build_why_card(
                        session,
                        repo_id,
                        path,
                        repo_path=repo_path,
                        provider=provider,
                    )
                built += 1
            except Exception as exc:  # noqa: BLE001
                errors += 1
                if errors <= 3:
                    print(f"    skip {path}: {exc}")
        card_secs = time.perf_counter() - t1
        print(
            f"  Why Cards: {built} built, {errors} skipped in {card_secs:.1f}s"
        )
        print()

    print("Done. Snapshots are in", settings.db_dir)


if __name__ == "__main__":
    main()
