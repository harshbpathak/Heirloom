# Harsh: demo, video and two Bob tasks

Shared setup, layout and team rules are in [README.md](README.md).

## 1. Demo and video

Follow the 3-minute script in spec §16.1. It needs:

- Ayush's hosted URL, or `heirloom serve` locally
- the Archivist mode in Bob (for the 1:00–1:40 segment)
- a real PR guard comment, which Bob task 2 below produces

The closing numbers to quote: tests passing, the number of sessions in `bob_sessions/`, and the fact that everything works offline.

## Before running Bob

1. From the repo root, run `heirloom ingest .` so the MCP tools have data about Heirloom itself.
2. Launch Bob from a terminal where `.venv` is active. `.bob/mcp.json` runs the `heirloom` command, so it must be on the PATH.
3. Export each session to `bob_sessions/NN-topic.md`, for example `01-mypy-strict.md` and `02-pr-guard.md`.

## 2. Bob task 1: mypy strict (Archivist mode)

Paste into Bob:

```
Make `python -m mypy core --python-version 3.12` report zero errors (currently 28 in 6 files).
Fix the types properly: no blanket `# type: ignore`, and no weakening mypy strict in pyproject.toml.
The one exception is the mypy python_version: set it to 3.12 in pyproject.toml, because numpy's stubs don't parse under 3.11.
Before editing each file, call ask_why and impact_if_changed on it. After a real design choice, call record_decision.
Run `python -m pytest -q` at the end: all 155 tests must still pass.
Commit in small steps with short plain messages (no feat:/fix: prefixes).
```

Done when `mypy core` reports zero errors and `pytest -q` is green.

## 3. Bob task 2: PR guard on a real PR (Code or Archivist mode)

Paste into Bob:

```
Add .github/workflows/heirloom-pr-guard.yml that runs the local ./action on pull_request events.
It needs actions/checkout with fetch-depth: 0 and permissions: pull-requests: write, contents: read.
Push it, then open a small test PR (for example, a harmless edit next to a DO NOT comment in core/)
and confirm the Heirloom comment appears. Push to the same PR again and confirm the comment is
updated in place, not posted twice. Report the PR URL and any failures from the Action log verbatim.
Commit with short plain messages.
```

Done when a PR shows one Heirloom comment that updates in place on a new push. Keep that PR for the video.

## Watch out

Bob task 1 edits type hints across 6 files in `core/`. Land it early and tell Daksh, because his backend tasks touch `core/services/whycard.py` and `core/trails/builder.py`.
