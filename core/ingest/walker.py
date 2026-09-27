"""File-tree walking with skip rules and language detection (spec F1 step 2)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "vendor",
    "__pycache__",
    ".venv",
    "venv",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
}

LOCKFILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "uv.lock",
    "Cargo.lock",
    "composer.lock",
    "Gemfile.lock",
}

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".svg",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".whl",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp3",
    ".mp4",
    ".mov",
    ".sqlite",
    ".db",
    ".pyc",
    ".class",
    ".jar",
    ".bin",
    ".wasm",
    ".min.js",
    ".min.css",
}

MAX_FILE_BYTES = 1_000_000

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
    ".md": "markdown",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".html": "html",
    ".css": "css",
    ".sh": "shell",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
}

# Languages that get import edges and blame analysis in v1 (spec F3).
ANALYZED_LANGUAGES = {"python", "javascript", "typescript", "vue"}


@dataclass
class WalkedFile:
    """A source file discovered during the walk."""

    path: str  # POSIX-style path relative to the repo root
    language: str | None
    loc: int


def detect_language(path: str) -> str | None:
    """Return the language for a path based on its extension, or None."""
    lower = path.lower()
    for ext, lang in LANGUAGE_BY_EXTENSION.items():
        if lower.endswith(ext):
            return lang
    return None


def should_skip(rel_path: Path, size: int) -> bool:
    """Apply the skip rules from spec F1 step 2 to one file."""
    parts = set(rel_path.parts[:-1])
    if parts & SKIP_DIRS:
        return True
    name = rel_path.name
    if name in LOCKFILES:
        return True
    lower = name.lower()
    for ext in BINARY_EXTENSIONS:
        if lower.endswith(ext):
            return True
    if size > MAX_FILE_BYTES:
        return True
    return False


def _git_tracked_files(repo_path: Path) -> list[str] | None:
    """Files tracked by git (this respects .gitignore); None if git fails."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8", errors="replace")
        return [p for p in out.split("\0") if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def count_loc(abs_path: Path) -> int:
    """Count non-empty lines in a text file; 0 on read errors."""
    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines() if line.strip())


def walk_repo(repo_path: Path) -> list[WalkedFile]:
    """Walk the repo and return files that pass the skip rules.

    Uses ``git ls-files`` when available so ``.gitignore`` is respected;
    falls back to a plain directory walk otherwise.
    """
    tracked = _git_tracked_files(repo_path)
    if tracked is not None:
        candidates = [Path(p) for p in tracked]
    else:
        candidates = [p.relative_to(repo_path) for p in repo_path.rglob("*") if p.is_file()]

    results: list[WalkedFile] = []
    for rel in candidates:
        abs_path = repo_path / rel
        if not abs_path.is_file():
            continue
        try:
            size = abs_path.stat().st_size
        except OSError:
            continue
        if should_skip(rel, size):
            continue
        posix = rel.as_posix()
        results.append(
            WalkedFile(path=posix, language=detect_language(posix), loc=count_loc(abs_path))
        )
    return results
