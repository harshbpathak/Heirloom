"""Import extraction and resolution for JS/TS/Vue and Python (spec F3 step 1).

Decision: regex parsers are used instead of tree-sitter so installation is
dependency-free and works everywhere (documented in docs/DECISIONS.md).
External packages are ignored; only imports resolving to repo files count.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

JS_IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w*{},\s$]+\s+from\s+)?|export\s+(?:[\w*{},\s$]+\s+from\s+)|require\(\s*|import\(\s*)['"]([^'"]+)['"]""",
)
PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import\s+([\w.*]+(?:\s+as\s+\w+)?(?:\s*,\s*[\w.*]+(?:\s+as\s+\w+)?)*)|import\s+([\w.]+(?:\s*,\s*[\w.]+)*))",
    re.MULTILINE,
)

JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue")
JS_INDEX_CANDIDATES = tuple(f"/index{ext}" for ext in JS_EXTENSIONS)


def extract_import_specs(text: str, language: str) -> list[str]:
    """Return the raw import specifiers found in a file's text."""
    if language == "python":
        specs: list[str] = []
        for match in PY_IMPORT_RE.finditer(text):
            if match.group(1):
                base = match.group(1)
                specs.append(base)
                # "from pkg import mod" may target a submodule: emit pkg.mod too.
                for name in (match.group(2) or "").split(","):
                    name = name.strip().split(" as ")[0].strip()
                    if name and name != "*":
                        specs.append(f"{base}.{name}" if not base.endswith(".") else base + name)
            elif match.group(3):
                specs.extend(m.strip() for m in match.group(3).split(","))
        return specs
    if language in ("javascript", "typescript", "vue"):
        source = text
        if language == "vue":
            # Only the <script> blocks of .vue files carry imports.
            blocks = re.findall(r"<script[^>]*>(.*?)</script>", text, re.DOTALL)
            source = "\n".join(blocks) if blocks else text
        return [m.group(1) for m in JS_IMPORT_RE.finditer(source)]
    return []


def resolve_js_import(src_path: str, spec: str, repo_files: set[str]) -> str | None:
    """Resolve a relative JS/TS import specifier to a repo file, or None."""
    if not spec.startswith("."):
        return None  # external package
    base = PurePosixPath(src_path).parent
    target = _normalize(base, spec)
    candidates = [target] + [target + ext for ext in JS_EXTENSIONS]
    candidates += [target + idx for idx in JS_INDEX_CANDIDATES]
    for cand in candidates:
        if cand in repo_files:
            return cand
    return None


def resolve_py_import(src_path: str, module: str, repo_files: set[str]) -> str | None:
    """Resolve a Python module path to a repo file, or None.

    Handles absolute module paths rooted at the repo and relative imports
    (leading dots) rooted at the importing file's package.
    """
    if module.startswith("."):
        depth = len(module) - len(module.lstrip("."))
        rest = module.lstrip(".")
        base = PurePosixPath(src_path).parent
        for _ in range(depth - 1):
            base = base.parent
        parts = ([str(base)] if str(base) != "." else []) + (rest.split(".") if rest else [])
    else:
        parts = module.split(".")

    # Try progressively shorter module paths ("pkg.mod.symbol" -> "pkg.mod").
    for end in range(len(parts), 0, -1):
        joined = "/".join(parts[:end])
        for cand in (f"{joined}.py", f"{joined}/__init__.py"):
            if cand in repo_files:
                return cand
    return None


def resolve_imports(src_path: str, language: str, text: str, repo_files: set[str]) -> set[str]:
    """All repo files imported by ``src_path`` (external packages ignored)."""
    resolved: set[str] = set()
    for spec in extract_import_specs(text, language):
        if language == "python":
            target = resolve_py_import(src_path, spec, repo_files)
        else:
            target = resolve_js_import(src_path, spec, repo_files)
        if target and target != src_path:
            resolved.add(target)
    return resolved


def _normalize(base: PurePosixPath, spec: str) -> str:
    """Join and normalize a relative specifier against a base directory."""
    combined = base / spec
    parts: list[str] = []
    for part in combined.parts:
        if part == ".":
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)
