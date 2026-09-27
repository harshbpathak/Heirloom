# Heirloom — Architecture & Internals

This document describes the internal structure of Heirloom for contributors and anyone integrating with the codebase directly.

---

## Module map

```
heirloom/
├── api/
│   └── main.py             FastAPI application; thin routes only
├── cli/
│   └── main.py             Typer CLI; 11 commands
├── mcp_server/
│   └── server.py           FastMCP server; 7 tools + 2 resources
├── web/                    React + TypeScript + Vite frontend
├── migrations/             Alembic migration scripts
├── tests/                  pytest suite; one module per subsystem
└── core/
    ├── config.py           Settings dataclass (env vars)
    ├── db.py               Session factory; per-repo SQLite routing
    ├── errors.py           Typed HeirloomError hierarchy
    ├── jobs.py             In-memory background job registry
    ├── timeutil.py         UTC-aware datetime helpers
    ├── ingest/
    │   ├── pipeline.py     Orchestrator — 8 stages, incremental
    │   ├── walker.py       File tree walk; language + LOC detection
    │   ├── gitlog.py       git log reader; LogEntry dataclass
    │   ├── blame.py        git blame → per-author line shares
    │   ├── comments.py     Intent comment extraction (FIXME, DO NOT, …)
    │   ├── docs.py         ADR / documentation file loader
    │   └── github_prs.py   GitHub REST API client for merged PRs
    ├── analysis/
    │   ├── coupling.py     Co-change coupling score computation
    │   ├── entry_points.py Entry-point detection heuristics
    │   ├── impact.py       Impact scoring from imports + coupling
    │   ├── imports_parser.py Static import edge resolver (8 languages)
    │   └── ownership.py    Ownership %, bus factor, at-risk, inactivity
    ├── decisions/
    │   ├── capture.py      .heirloom/decisions/*.md record format
    │   ├── dedupe.py       Decision deduplication by similarity
    │   └── extraction.py   Candidate filter, heuristic & LLM extraction
    ├── search/
    │   └── index.py        BM25 index over decisions (rank-bm25)
    ├── services/
    │   ├── ask.py          Q&A: BM25 retrieval + LLM synthesis
    │   ├── capture_service.py  Manual decision writing (DB + file)
    │   ├── queries.py      Read-side helpers shared by all surfaces
    │   └── whycard.py      Why Card assembly + rendering
    ├── export/
    │   └── exporter.py     Markdown + JSON knowledge-base export
    ├── llm/
    │   ├── provider.py     Provider abstraction + LLM cache
    │   ├── prompts_loader.py  Prompt file loader
    │   └── prompts/        Prompt templates (*.txt)
    ├── models/
    │   ├── db_models.py    SQLAlchemy 2.x ORM models
    │   └── schemas.py      Pydantic v2 response schemas
    └── trails/
        └── builder.py      Onboarding trail builder
```

---

## Dependency rule

**All three surfaces (CLI, API, MCP) import from `core/`. `core/` never imports from any surface.**

```
cli/     api/     mcp_server/
  └────────┴──────────┘
            │
          core/
```

This keeps the core testable in isolation and ensures there is no business logic duplication.

---

## Data storage

### Per-repo SQLite

Each ingested repo gets its own SQLite database file at:

```
~/.heirloom/db/<repo_id>.sqlite
```

Where `repo_id` is derived from the source path or URL via `repo_id_from_source()` in `core/db.py`.

Schema is managed by [Alembic](https://alembic.sqlalchemy.org/). Migrations live in `migrations/`.

### Remote repo cache

GitHub URLs are shallow-cloned to:

```
~/.heirloom/cache/<owner>__<repo>/
```

Re-ingesting runs `git fetch` on the existing clone rather than re-cloning.

### LLM response cache

All LLM calls go through `cached_complete_json()` in `core/llm/provider.py`. Responses are stored in the `llm_cache` table, keyed by `SHA256(prompt + input)`. Identical calls are served from cache with no network request.

---

## ORM data model

All tables live in `core/models/db_models.py`.

### `Repo`

| Column | Type | Description |
|---|---|---|
| `id` | string PK | Derived from source path/URL |
| `name` | string | Repository name |
| `source` | string | Original source (path or URL) |
| `default_branch` | string | e.g. `main` |
| `last_ingested_commit` | string? | HEAD at last successful ingest |
| `ingested_at` | datetime? | Timestamp of last ingest |
| `stats_json` | text? | Cached aggregate stats |

### `File`

| Column | Type | Description |
|---|---|---|
| `id` | int PK | |
| `repo_id` | FK → Repo | |
| `path` | string | Repo-relative path |
| `language` | string? | Detected language |
| `loc` | int | Lines of code |
| `is_entry_point` | bool | True if detected as an entry point |
| `fan_in` | int | Number of files that import this one |
| `fan_out` | int | Number of files this one imports |
| `bus_factor` | int? | Minimum owners needed for 50% coverage |
| `at_risk` | bool | `bus_factor == 1` and sole owner is inactive |
| `summary` | text? | Cached file summary |
| `summary_source` | string | `llm`, `comment`, or `none` |

### `Author`

Canonical author identity. Multiple git email addresses are merged into one `Author` row during ingestion using fuzzy name matching and optional alias overrides.

| Column | Type | Description |
|---|---|---|
| `id` | int PK | |
| `repo_id` | FK → Repo | |
| `canonical_name` | string | Merged display name |
| `emails_json` | text | JSON array of all known emails |

### `Ownership`

Per-file per-author ownership score.

| Column | Type | Description |
|---|---|---|
| `file_id` | FK → File (PK) | |
| `author_id` | FK → Author (PK) | |
| `blame_share` | float | Fraction of current lines attributed to this author |
| `recent_share` | float | Fraction of recent-window commits touching this file |
| `ownership` | float | Weighted blend: `0.7 * blame_share + 0.3 * recent_share` |
| `last_commit_at` | datetime? | Author's most recent commit touching this file |

**Bus factor** is computed as the minimum number of authors needed to cover 50% of a file's lines (from `blame_share`).

**At-risk** is set when `bus_factor == 1` and the sole owner's last commit anywhere in the repo is older than 180 days.

### `Commit` / `CommitFile`

Git commit history. `CommitFile` records the number of added and deleted lines per file per commit, used for co-change coupling.

### `Import`

Static import edges: `src_file_id → dst_file_id`. Populated by `core/analysis/imports_parser.py` for Python, JavaScript, TypeScript, Go, Java, Ruby, Rust, and C/C++.

### `Coupling`

Co-change coupling between pairs of files.

| Column | Type | Description |
|---|---|---|
| `file_a_id` | FK → File (PK) | |
| `file_b_id` | FK → File (PK) | |
| `co_changes` | int | Number of commits where both files changed |
| `score` | float | `co_changes / max(changes_a, changes_b)` (Jaccard-like) |

### `Evidence`

A raw source from which decisions were extracted or that corroborates a decision.

| Column | Type | Values |
|---|---|---|
| `type` | string | `commit`, `pull_request`, `code_comment`, `doc`, `adr`, `manual` |
| `ref` | string | Unique reference within the type (commit hash, PR number, file path, …) |
| `url` | string? | Link to the original source |
| `text` | text | Full text of the evidence |

### `Decision`

A recorded reason behind a piece of code — either extracted automatically or entered manually.

| Column | Type | Description |
|---|---|---|
| `title` | string | Max 80 chars |
| `summary` | text | Short summary |
| `reasoning` | text | Full reasoning |
| `alternatives` | text? | Alternatives that were considered |
| `confidence` | string | `high` (ADR), `medium` (LLM), `low` (heuristic) |
| `source` | string | `extracted` or `manual` |
| `skill_hash` | string? | SHA-256 of the Bob skill that recorded this, if any |
| `author` | string? | Manual override author name |

`DecisionEvidence` and `DecisionFile` are join tables linking decisions to their evidence and files respectively.

### `Job`

Background ingestion job with progress tracking. Status transitions: `pending → running → done | failed`.

### `LLMCache`

`key = SHA256(prompt + input)`, `response = raw JSON string from the LLM`.

---

## Ingestion pipeline

Defined in `core/ingest/pipeline.py`. The main entry point is `ingest_repo()`.

### Stage sequence

| % | Stage | What happens |
|---|---|---|
| 5% | Prepare | Resolve local path or shallow-clone GitHub URL |
| 15% | Walk | Discover all source files; record language + LOC |
| 30% | Git log | Read commits (incremental: only since `last_ingested_commit`); merge author identities |
| 55% | Blame | Per-file `git blame` (incremental: only changed files) |
| 65% | Comments & docs | Extract intent comments; load ADR/doc files; fetch GitHub PRs |
| 75% | Structure | Imports, coupling, ownership, bus factor, at-risk |
| 90% | Decisions | Keyword filter → heuristic or LLM extraction → deduplication → persist |
| 100% | Done | Update `last_ingested_commit`, `ingested_at`, `stats_json` |

### Incremental re-ingest

On subsequent runs, `ingest_repo()` detects that `last_ingested_commit == HEAD` (already up to date) and returns immediately. Otherwise it processes only commits after `last_ingested_commit` and only re-blames files touched by those commits.

### Author identity merging

`merge_identities()` in `core/analysis/ownership.py` uses:

1. Exact email match.
2. Fuzzy name match (RapidFuzz, threshold 90%).
3. Manual alias overrides from `.heirloom/aliases.yml` inside the repo.

---

## Decision extraction

Defined in `core/decisions/extraction.py`.

### Candidate filter

An `EvidenceCandidate` passes if:

- Type is `code_comment` or `adr` → always a candidate.
- Type is `commit` and message length > 60 chars, **or** contains a keyword from `CANDIDATE_KEYWORDS` (`because`, `instead`, `so that`, `revert`, `workaround`, `migrate`, `replace`, `deprecate`, `fix race`, `perf`).
- Type is `pull_request` and body length > 100 chars.

### Heuristic path (no LLM)

For each candidate:

- **Title** = first line, truncated to 80 chars.
- **Summary** = first 2 sentences of the body.
- **Reasoning** = sentences containing `because`, `so that`, `instead of`, or `to avoid`.
- **Confidence** = `high` for ADRs; `low` otherwise.

### LLM path

Candidates are batched in groups of 10 and sent to the LLM with the `decision_extraction` prompt. The prompt returns a structured JSON array of `ExtractionResult` objects. Invalid responses fall back to heuristic extraction for that batch.

LLM-extracted decisions get confidence `high` (ADR source) or `medium` (all other types).

### Deduplication

`core/decisions/dedupe.py` merges decisions with highly similar titles using fuzzy string matching before persistence. The higher-confidence version is kept.

---

## Why Card assembly

`core/services/whycard.py::build_why_card()`:

1. Load the `File` row; raise `FileNotFoundInRepoError` if absent.
2. Query decisions, holders, impact, warnings, and activity from the database.
3. Generate or retrieve the file summary:
   - If `file_row.summary` is cached and source is not `none`, return it.
   - If an LLM is available: send file content + decision titles → `file_summary` prompt → cache and return.
   - Fall back to the file's header comment (docstring or `//` block).
   - Final fallback: `"No summary available"` with source `none`.
4. Persist updated summary if it changed.
5. Return a `WhyCard` Pydantic model.

---

## Impact scoring

`core/analysis/impact.py::compute_impact()`:

Score for a candidate file `C` relative to the changed file `F`:

```
import_score   = 1.0  if C imports F (direct import edge)
coupling_score = coupling.score  if (F, C) is in the coupling table
change_weight  = log(1 + changes_C) / log(1 + max_changes)

score = max(import_score, coupling_score) * change_weight
```

Results are sorted by score descending. Human-readable `reason` is either `"imports <filename>"` (import edge) or `"co-changed N times"` (coupling).

---

## LLM provider abstraction

`core/llm/provider.py::LLMProvider`:

- `available: bool` — whether the provider is configured.
- `name: str` — `"watsonx"`, `"openai_compat"`, or `"none"`.
- `complete_json(prompt, input) -> dict` — call the model, parse JSON response.

`cached_complete_json(provider, session, prompt, input)`:

1. Compute key = `SHA256(prompt + input)`.
2. Check `llm_cache` table; return cached value if found.
3. Call `provider.complete_json(prompt, input)`.
4. Store response in `llm_cache`.
5. Return parsed dict.

---

## Testing

Tests live in `tests/`. Each file covers one subsystem. A synthetic git repo is created on demand by `tests/fixtures/make_repo.py` and shared via a pytest `conftest.py` session fixture backed by in-memory SQLite.

```bash
pytest -q                                        # all tests
pytest tests/test_pipeline.py -q                 # one module
pytest -q --cov=core --cov-report=term-missing   # with coverage
```

CI enforces ≥80% branch coverage on `core/`.
