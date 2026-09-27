# now we are at the end..explain the whole workflow and the project

---

**Status:** active  **Date:** 2026-09-27

---

### 👤 User

now we are at the end..explain the whole workflow and the project

---

### 🤖 Assistant

> 🔧 called: list_files

Let me explore the project structure first to give you an accurate explanation.

> 🔧 **list_files** — .

### 🤖 Assistant

> 🔧 called: list_files, read_file



> 🔧 **read_file** — README.md

> 🔧 **list_files** — .

### 🤖 Assistant

> 🔧 called: read_file, list_files, list_files



> 🔧 **list_files** — api

> 🔧 **read_file** — pyproject.toml

> 🔧 **list_files** — core

### 🤖 Assistant

> 🔧 called: list_files, list_files, list_files



> 🔧 **list_files** — mcp_server

> 🔧 **list_files** — cli

> 🔧 **list_files** — tests

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file



> 🔧 **read_file** — cli/main.py

> 🔧 **read_file** — mcp_server/server.py

> 🔧 **read_file** — api/main.py

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — core/models/db_models.py

> 🔧 **read_file** — core/ingest/pipeline.py

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — core/ingest/pipeline.py

> 🔧 **read_file** — core/services/whycard.py

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file



> 🔧 **read_file** — core/config.py

> 🔧 **read_file** — Makefile

> 🔧 **read_file** — .github/workflows/ci.yml

### 🤖 Assistant

> 🔧 called: list_files, read_file



> 🔧 **list_files** — web

> 🔧 **read_file** — core/decisions/extraction.py

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — web/src

> 🔧 **read_file** — core/services/queries.py

### 🤖 Assistant

> 🔧 called: create_html_artifact

Now I have a thorough picture of the entire project. Let me produce the one-pager.

> 🔧 **create_html_artifact** — heirloom_overview

### 🤖 Assistant

Here's the complete picture:

---

## What Heirloom Is

**Heirloom** is a code intelligence tool that answers three questions about any git repository:

> *Why* is this file the way it is? *Who* still understands it? *What breaks* if I change it?

It is defined by the tag in [`pyproject.toml`](pyproject.toml:4): *"Heirloom tells you why code is the way it is, who still understands it, and what breaks if you change it."*

---

## The Workflow, End to End

### 1. Ingest
You point Heirloom at a local git repo or a GitHub URL:
```
heirloom ingest ./my-repo
# or
heirloom ingest https://github.com/org/repo
```
The pipeline in [`core/ingest/pipeline.py`](core/ingest/pipeline.py) runs 8 sequential stages:

| Stage | What it does |
|---|---|
| Resolve / clone | Shallow-clones GitHub URLs into `~/.heirloom/cache/` |
| Walk file tree | Finds every source file, records language + LOC |
| Git log | Reads up to 2 000 commits; merges author aliases |
| Git blame | Per-file line attribution for ownership |
| Comments & docs | Extracts `FIXME`/`DO NOT`/`HACK` comments + ADR files |
| GitHub PRs | Fetches merged PR bodies as evidence (needs `GITHUB_TOKEN`) |
| Analysis | Resolves import edges, computes co-change coupling, calculates per-author ownership %, bus factor, at-risk flag |
| Decision extraction | Keyword filter → heuristic decisions; optional LLM batch → higher-confidence decisions; deduplication |

Everything persists into **one SQLite file per repo** at `~/.heirloom/db/<repo_id>.sqlite`.

---

### 2. Core Services (the knowledge layer)
All three surfaces (CLI, API, MCP) delegate to [`core/services/`](core/services/):

- **[`whycard.py`](core/services/whycard.py)** — assembles the *Why Card*: LLM summary (falls back to header comment), linked decisions, knowledge holders, impact set, and HACK/DO-NOT warnings.
- **[`queries.py`](core/services/queries.py)** — shared read helpers: holders, impact, decisions per file, risk report, repo tree.
- **[`ask.py`](core/services/ask.py)** — BM25 search over decisions → LLM answer with citations.
- **[`capture_service.py`](core/services/capture_service.py)** — writes a manual decision to SQLite *and* to `.heirloom/decisions/NNNN-slug.md` inside the target repo.
- **[`trails/builder.py`](core/trails/builder.py)** — generates an ordered onboarding reading path through the codebase.

---

### 3. Three Surfaces

| Surface | File | Key feature |
|---|---|---|
| **CLI** | [`cli/main.py`](cli/main.py) | `ingest`, `why`, `who`, `impact`, `trail`, `ask`, `decide`, `risk`, `export`, `serve`, `mcp` |
| **REST API** | [`api/main.py`](api/main.py) | Thin FastAPI routes; serves the React web UI from `web/dist` |
| **MCP Server** | [`mcp_server/server.py`](mcp_server/server.py) | 7 tools (`ask_why`, `who_knows`, `impact_if_changed`, `onboarding_trail`, `search_decisions`, `record_decision`, `repo_risk_report`) + 2 resources; plugs into AI coding assistants |

---

### 4. LLM (optional)
Configured via env vars in [`core/config.py`](core/config.py). Supports **IBM watsonx.ai (Granite)** and any **OpenAI-compatible endpoint**. All LLM calls go through `cached_complete_json()` — responses are stored in `llm_cache` and replayed on identical prompts. Everything degrades gracefully to heuristics when no LLM is set.

---

### 5. CI & Tooling
- **[`Makefile`](Makefile)**: `install`, `dev`, `test`, `lint`, `demo`
- **[`.github/workflows/ci.yml`](.github/workflows/ci.yml)**: two parallel jobs — Python (ruff + pytest ≥80% coverage) and Web (pnpm lint + test + build)
- **18 test modules** in [`tests/`](tests/) using an in-memory SQLite fixture and a synthetic git repo factory

---

### 👤 User

write the documention for the project

---

### 🤖 Assistant

> 🔧 called: read_file, read_file

Let me read the current state of all the externally modified files before writing documentation.

> 🔧 **read_file** — core/services/queries.py

> 🔧 **read_file** — core/decisions/extraction.py

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — core/models/db_models.py

> 🔧 **read_file** — core/ingest/pipeline.py

### 🤖 Assistant

> 🔧 called: read_file, read_file, read_file



> 🔧 **read_file** — mcp_server/server.py

> 🔧 **read_file** — api/main.py

> 🔧 **read_file** — cli/main.py

### 🤖 Assistant

> 🔧 called: read_file, read_file

Now let me also read the remaining core files and the `.env.example` before writing:

> 🔧 **read_file** — .env.example

> 🔧 **read_file** — core/ingest/pipeline.py

### 🤖 Assistant

> 🔧 called: update_todo_list

Now I have everything I need. Let me write the full documentation:

> 🔧 **update_todo_list** — 
[-] Write README.md — complete project documentation
[ ] Write docs/api.md — REST API reference
[ ] Write docs/cli.md — CLI reference
[ ] Write docs/mcp.md — MCP server reference
[ ] Write docs/architecture.md — internals & data model


### 🤖 Assistant

> 🔧 called: write_file



> 🔧 **write_file** — README.md

### 🤖 Assistant

> 🔧 called: update_todo_list

Now write the four `docs/` pages in parallel:

> 🔧 **update_todo_list** — 
[x] Write README.md — complete project documentation
[-] Write docs/api.md — REST API reference
[-] Write docs/cli.md — CLI reference
[-] Write docs/mcp.md — MCP server reference
[-] Write docs/architecture.md — internals & data model


### 🤖 Assistant

> 🔧 called: write_file, write_file, write_file, write_file



> 🔧 **write_file** — docs/api.md

> 🔧 **write_file** — docs/cli.md

> 🔧 **write_file** — docs/architecture.md

> 🔧 **write_file** — docs/mcp.md

### 🤖 Assistant

> 🔧 called: update_todo_list



> 🔧 **update_todo_list** — 
[x] Write README.md — complete project documentation
[x] Write docs/api.md — REST API reference
[x] Write docs/cli.md — CLI reference
[x] Write docs/mcp.md — MCP server reference
[x] Write docs/architecture.md — internals & data model


### 🤖 Assistant

Five documentation files written. Here's what was created:

---

### [`README.md`](README.md)
The main project README — full install instructions, quick-start, feature table, complete CLI reference (all 11 commands with flags and examples), REST API table, MCP setup snippets, LLM integration guide (watsonx.ai + OpenAI-compatible), architecture overview, and dev/CI commands.

### [`docs/api.md`](docs/api.md)
Deep REST API reference — every endpoint with method, path, query params, request body schema, and full example response JSON. Covers the error envelope format, all HTTP status codes, and the three `?format=` modes for the Why Card.

### [`docs/cli.md`](docs/cli.md)
CLI reference — full `Usage:` block for each command, all flags, concrete examples, and sample Rich table output so readers know exactly what to expect on screen vs `--json`.

### [`docs/mcp.md`](docs/mcp.md)
MCP server reference — stdio and HTTP setup configs, repo auto-resolution order, the 2 000-token response budget, full parameter/response tables for all 7 tools, both resource URIs, and a recommended usage pattern (ask_why → impact_if_changed → record_decision).

### [`docs/architecture.md`](docs/architecture.md)
Internals guide — annotated module map, the `core/`-only dependency rule, storage layout (per-repo SQLite, remote clone cache, LLM cache), full ORM column-level table reference, the 8-stage ingestion pipeline with incremental re-ingest logic, decision extraction (candidate filter → heuristic vs LLM path → deduplication), Why Card assembly, impact scoring formula, LLM provider abstraction, and testing setup.