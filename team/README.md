# Heirloom team plan

Who owns the remaining work. The core product is built and tested; what's left is hosting, polish, demo data, docs and the video.

| Person | Owns | Brief |
|---|---|---|
| Harsh | Demo script and video; two Bob tasks (mypy cleanup, PR guard on a real PR) | [HARSH.md](HARSH.md) |
| Ayush | Hosting: web UI on Vercel, API on Render, public demo URL | [AYUSH.md](AYUSH.md) |
| Daksh | Demo snapshots, UI polish and accessibility, remaining backend tasks | [DAKSH.md](DAKSH.md) |
| Bob IDE | All docs in spec §16 (**driver not assigned yet**) | [Docs via Bob](#docs-via-bob-unassigned) below |

**Order that matters:** Daksh's demo snapshots, then Ayush's hosted demo, then Harsh records the video. Ayush can deploy earlier with a placeholder database.

## Current state

- Repo: https://github.com/harshbpathak/Heirloom
- 155 Python tests and 9 web tests pass, with 87% coverage on `core/`.
- Runs fully offline with zero API keys.
- Everything works locally: ingestion, analysis, decisions, search and Ask, Why Cards, trails, the REST API, the CLI, the MCP server, all 7 web pages, the Bob mode and skills, and the PR guard Action.

## Set up and run locally

```bash
git clone https://github.com/harshbpathak/Heirloom.git && cd Heirloom
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"        # macOS/Linux: .venv/bin/pip
cd web && pnpm install && pnpm build && cd ..

# Sample data: build the test fixture repo and ingest it
python tests/fixtures/make_repo.py ../heirloom-fixture
heirloom ingest ../heirloom-fixture

heirloom serve                                # http://localhost:8000
```

For UI work with hot reload, run `uvicorn api.main:app --reload --port 8000` and `pnpm dev` in `web/`. The dev server on port 5173 proxies `/api` to 8000.

```bash
pytest -q                                     # Python tests, about 5 seconds
cd web && pnpm test && pnpm lint && pnpm build
```

## Layout

| Path | What lives there |
|---|---|
| `core/` | All logic. The API, CLI and MCP server are thin wrappers over it; never duplicate logic. |
| `api/main.py` | FastAPI. Serves `/api/*`, and serves the built UI with a single-page-app fallback under `heirloom serve`. |
| `cli/main.py` | The `heirloom` command. |
| `mcp_server/server.py` | Seven MCP tools for agents. |
| `web/` | React, TypeScript, Vite, Tailwind and D3. Calls the API with relative `/api/...` URLs. |
| `action/` | PR guard GitHub Action. |
| `tests/` | pytest. `tests/fixtures/make_repo.py` builds a small deterministic git repo. |
| `.bob/` | Bob's Archivist mode, two skills and MCP config. |

## Team rules

- Work on your own branch (`ayush/hosting`, `daksh/ui`) and merge through a PR. CI runs lint and tests on every PR.
- Commit messages are short and plain, with no `feat:` or `chore:` prefixes (for example "Add PR guard action").
- Never invent data in the UI. An unknown value shows "unknown" and the reason.
- Everything must keep working with zero API keys. Never commit secrets; set them in hosting dashboards.
- New code gets tests. Keep the existing ones passing.

## Docs via Bob (unassigned)

Someone needs to drive these Bob sessions and export each one to `bob_sessions/NN-topic.md`.

Still to write: `README.md` (the current one is a stub), `docs/ARCHITECTURE.md`, `docs/MCP.md`, `docs/BOB.md`, `docs/API.md`, `docs/DECISIONS.md`, `docs/DEMO.md`, `docs/SUBMISSION.md`, `CONTRIBUTING.md` and `CHANGELOG.md`. Heirloom's own decisions should also go into `.heirloom/decisions/`, so the project documents itself with its own tool.

Facts the docs must get right:

- `docs/BOB.md` must say plainly that the core build was done in Claude Code, not Bob, and that Bob's MCP Builder was not used. Only real Bob sessions go in its sessions table.
- Bob's config paths, read from the installed Bob extension: `.bob/custom_modes.yaml`, `.bob/skills/<name>/SKILL.md` and `.bob/mcp.json`. Bob calls the spec's "command" tool group `execute`.
- The OpenAPI spec is served at `/api/openapi.json`, with interactive docs at `/api/docs`.
- Build choices worth recording in `docs/DECISIONS.md`:
  - regex import parsers instead of tree-sitter
  - `ruff format` instead of black, because black refuses to run on Python 3.12.5
  - plain commit messages, by team choice
  - unknown decision dates stay unknown instead of defaulting to today
  - the 3 demo repos Daksh picks, and why
