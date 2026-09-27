"""Line ownership via ``git blame --line-porcelain`` (spec F1 step 4)."""

from __future__ import annotations

import subprocess
from collections import defaultdict
from pathlib import Path


def blame_shares(repo_path: Path, rel_path: str) -> dict[tuple[str, str], int]:
    """Map ``(author_name, author_email) -> surviving line count`` for one file.

    Returns an empty dict when blame fails (e.g. file not tracked).
    """
    try:
        raw = subprocess.run(
            ["git", "blame", "--line-porcelain", "--", rel_path],
            cwd=repo_path,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return {}

    counts: dict[tuple[str, str], int] = defaultdict(int)
    current_author: str | None = None
    current_email: str | None = None
    for line in raw.split("\n"):
        if line.startswith("author "):
            current_author = line[len("author ") :].strip()
        elif line.startswith("author-mail "):
            current_email = line[len("author-mail ") :].strip().strip("<>")
        elif line.startswith("\t"):
            # A tab-prefixed line is the actual file content for one blamed line.
            if current_author is not None:
                counts[(current_author, current_email or "")] += 1
    return dict(counts)
