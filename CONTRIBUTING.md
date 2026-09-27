# Contributing

## Setup

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # macOS/Linux: .venv/bin/pip
cd web && pnpm install
```

## Before you open a PR

```bash
pytest -q
ruff check core api cli mcp_server tests
ruff format --check core api cli mcp_server tests
mypy core
cd web && pnpm lint && pnpm test && pnpm build
```

CI runs the same checks. The Heirloom PR guard also comments on your PR with the recorded decisions your change may conflict with.

## Rules

- All logic lives in `core/`. The API, CLI and MCP server only call it.
- Every LLM feature needs a deterministic fallback; the app must run with zero keys.
- Never invent data. Show "unknown" and the reason instead.
- Never commit secrets. Add new settings to `.env.example`.
- New code gets tests against the fixture repo (`tests/fixtures/make_repo.py`).
- Commit messages are short and plain, with no `feat:`/`fix:` prefixes.
- If your change is a real design choice, record it: `heirloom decide "title" --files ... --why "..."`.

Agents: see [AGENTS.md](AGENTS.md).
