# AGENTS.md

Guidance for AI coding agents (IBM Bob, Claude Code, Cursor, Copilot, and others)
working in this repository.

## Project layout

| Path | What lives there |
|---|---|
| `core/` | All logic, as a Python package. `ingest/` (git, blame, comments, docs, PRs), `analysis/` (imports, coupling, ownership, impact), `decisions/` (extraction, dedupe, capture), `search/` (BM25), `trails/`, `llm/` (providers and prompts), `services/` (Why Card, ask, queries), `models/` (SQLAlchemy and Pydantic) |
| `api/` | FastAPI app. Routes are thin and call `core`. |
| `cli/` | Typer CLI (`heirloom ...`). |
| `mcp_server/` | FastMCP server exposing `core` to agents. |
| `web/` | React, TypeScript, Vite, Tailwind and D3 UI. Tests are in `web/src/__tests__/`. |
| `action/` | GitHub Action (PR guard). |
| `tests/` | pytest suite. `tests/fixtures/make_repo.py` builds a deterministic git repo. |
| `.bob/` | Bob custom mode, skills and MCP config. |
| `.heirloom/decisions/` | Heirloom's own decision records (the project documents itself). |

The API, CLI and MCP server share `core`. Never duplicate logic across them.

## Running things

```bash
python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"   # Windows
python -m venv .venv && .venv/bin/pip install -e ".[dev]"       # macOS/Linux
pytest -q                          # Python tests (no network, no keys)
pytest -q --cov=core               # with coverage (target 80% on core/)
cd web && pnpm install && pnpm test && pnpm build
ruff check core api cli mcp_server tests && ruff format --check core api cli mcp_server tests
```

## Conventions

- Python 3.11+, type hints everywhere, and a docstring on every public function. Format with `ruff format` (black-compatible). Lint with `ruff check`. Run mypy strict on `core/`.
- TypeScript runs in strict mode. Don't use `any` without a comment explaining why. Lint with ESLint.
- Commit messages are short and plain, with no `feat:`/`chore:` prefixes (for example "Add PR guard action"). The project owner chose this over the Conventional Commits style in spec §12.
- Errors are custom exceptions in `core/errors.py`, and the API maps them to `{"error": {"code", "message"}}`.
- Every LLM feature needs a deterministic fallback. The app must run with zero API keys.
- Never invent data. If a value is unknown, return or show "unknown" with the reason.
- Never hardcode secrets. Read them from the environment and document them in `.env.example`.
- Every new module gets unit tests against the fixture repo.

## Heirloom MCP server

This repo ships an MCP server (`heirloom mcp`), and `.bob/mcp.json` registers it for Bob.
Before editing core modules (`core/ingest/pipeline.py`, `core/analysis/*`,
`core/decisions/*`, `core/services/*`), call:

1. `ask_why(path)` to read the recorded decisions and DO NOT warnings.
2. `impact_if_changed(path)` to see what else may break.

If your change contradicts a recorded decision, stop and ask the user. After a real
design choice, call `record_decision` so the reasoning lands in `.heirloom/decisions/`.
To index this repo itself, run `heirloom ingest .` from the root.
