"""Entry-point detection (spec F3 step 5)."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path, PurePosixPath

ENTRY_STEMS = {"main", "index", "app", "server", "cli", "__main__"}


def detect_entry_points(repo_path: Path, repo_files: list[str]) -> set[str]:
    """Mark entry points: files named main/index/app/server/cli/__main__,
    or referenced in package.json main/bin/scripts or pyproject.toml scripts."""
    file_set = set(repo_files)
    entries: set[str] = set()

    for path in repo_files:
        stem = PurePosixPath(path).stem
        if stem in ENTRY_STEMS:
            entries.add(path)

    entries |= _package_json_entries(repo_path, file_set)
    entries |= _pyproject_entries(repo_path, file_set)
    return entries


def _package_json_entries(repo_path: Path, file_set: set[str]) -> set[str]:
    """Entry files referenced by package.json main/bin/scripts."""
    pkg = repo_path / "package.json"
    if not pkg.is_file():
        return set()
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()

    refs: set[str] = set()
    main = data.get("main")
    if isinstance(main, str):
        refs.add(main)
    bin_field = data.get("bin")
    if isinstance(bin_field, str):
        refs.add(bin_field)
    elif isinstance(bin_field, dict):
        refs.update(v for v in bin_field.values() if isinstance(v, str))
    for script in (data.get("scripts") or {}).values():
        if isinstance(script, str):
            # Pull file-looking tokens out of script commands (e.g. "node src/server.js").
            refs.update(re.findall(r"[\w./-]+\.(?:js|mjs|cjs|ts|tsx|jsx)", script))

    return {_norm(r) for r in refs if _norm(r) in file_set}


def _pyproject_entries(repo_path: Path, file_set: set[str]) -> set[str]:
    """Entry files referenced by pyproject.toml [project.scripts] modules."""
    py = repo_path / "pyproject.toml"
    if not py.is_file():
        return set()
    try:
        data = tomllib.loads(py.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return set()

    entries: set[str] = set()
    scripts = (data.get("project") or {}).get("scripts") or {}
    for target in scripts.values():
        if not isinstance(target, str):
            continue
        module = target.split(":")[0]
        candidate = module.replace(".", "/") + ".py"
        if candidate in file_set:
            entries.add(candidate)
        init_candidate = module.replace(".", "/") + "/__init__.py"
        if init_candidate in file_set:
            entries.add(init_candidate)
    return entries


def _norm(ref: str) -> str:
    """Normalize a package.json path reference to a repo-relative POSIX path."""
    return ref.lstrip("./").replace("\\", "/")
