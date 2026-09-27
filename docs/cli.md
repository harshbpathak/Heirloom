# Heirloom CLI Reference

The `heirloom` CLI is built with [Typer](https://typer.tiangolo.com/) and [Rich](https://github.com/Textualize/rich). Every command prints human-friendly output by default and emits machine-readable JSON with `--json`.

**Entry point:** `heirloom` (installed via `pip install -e .`)

---

## Global conventions

- **`--repo <id-or-path>`** — Target a specific ingested repo. Can be a repo ID (slug) or a local filesystem path. When only one repo has been ingested, `--repo` can be omitted.
- **`--json`** — Print raw JSON to stdout instead of formatted Rich output. Exit code is still non-zero on errors.
- Errors print `error (<code>): <message>` to stderr and exit with code 1.

---

## `heirloom ingest <source>`

Ingest (or incrementally re-ingest) a repository. Builds the full knowledge base: git history, blame, intent comments, docs, GitHub PRs (optional), import graph, co-change coupling, ownership, and decision extraction.

```
Usage: heirloom ingest [OPTIONS] SOURCE

Arguments:
  SOURCE  Local path or public GitHub URL  [required]

Options:
  --since TEXT         Only commits after this date (ISO format: 2024-01-01)
  --max-commits INT    Commit limit (default: HEIRLOOM_MAX_COMMITS or 2000)
  --json               Emit JSON output
  --help               Show this message and exit.
```

**Examples**

```bash
heirloom ingest /path/to/my-repo
heirloom ingest https://github.com/org/my-repo
heirloom ingest https://github.com/org/my-repo --since 2024-01-01
heirloom ingest /path/to/my-repo --max-commits 500 --json
```

**Re-ingesting** is incremental: only commits after `last_ingested_commit` are processed, and only files touched by those commits are re-blamed.

**JSON output**
```json
{
  "repo_id": "my-repo",
  "stats": {
    "files": 312,
    "commits": 1840,
    "decisions": 47,
    "at_risk_files": 3
  }
}
```

---

## `heirloom why <file>`

Print the **Why Card** for a file: summary, recorded decisions, knowledge holders, impact set, and any `DO NOT` / `HACK` warnings.

```
Usage: heirloom why [OPTIONS] FILE

Arguments:
  FILE  Repo-relative file path  [required]

Options:
  --repo TEXT   Repo ID or local path
  --json        Emit JSON output
  --help        Show this message and exit.
```

**Examples**

```bash
heirloom why src/payments/processor.py
heirloom why src/payments/processor.py --json
heirloom why src/payments/processor.py --repo my-other-repo
```

The human output renders as Rich Markdown in the terminal. The JSON output includes `path`, `language`, `loc`, `is_entry_point`, `summary`, `summary_source`, `decisions`, `holders`, `bus_factor`, `at_risk`, `impact`, `warnings`, and `activity`.

---

## `heirloom who <path>`

Knowledge holders and bus factor for a file or directory. Accepts a single file path or a directory prefix (all matching files are shown).

```
Usage: heirloom who [OPTIONS] PATH

Arguments:
  PATH  File or directory  [required]

Options:
  --repo TEXT   Repo ID or local path
  --json        Emit JSON output
  --help        Show this message and exit.
```

**Examples**

```bash
heirloom who src/payments/processor.py
heirloom who src/payments/             # all files under the directory
heirloom who src/ --json
```

**Table output**

```
                   Knowledge holders: src/payments/processor.py
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ File                              ┃ Bus factor ┃ Holders                                             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ src/payments/processor.py         │ 1 AT RISK  │ Alice 87% (inactive), Bob 13%                       │
└───────────────────────────────────┴────────────┴─────────────────────────────────────────────────────┘
```

`AT RISK` is shown in red when `bus_factor == 1` and the sole owner is inactive (no commit in 180 days).

---

## `heirloom impact <file>`

Files most likely to break if this file changes, ranked by score with a human-readable reason.

```
Usage: heirloom impact [OPTIONS] FILE

Arguments:
  FILE  [required]

Options:
  --repo TEXT    Repo ID or local path
  --limit INT    Number of results (default: 10)
  --json         Emit JSON output
  --help         Show this message and exit.
```

**Examples**

```bash
heirloom impact src/payments/processor.py
heirloom impact src/payments/processor.py --limit 20
```

**Table output**

```
               Impact if src/payments/processor.py changes
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ File                          ┃ Score ┃ Reason                          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ tests/test_payments.py        │ 0.91  │ imports processor               │
│ src/webhooks/handler.py       │ 0.54  │ co-changed 12 times             │
└───────────────────────────────┴───────┴─────────────────────────────────┘
```

---

## `heirloom trail`

Generate an onboarding reading trail through the repo — an ordered list of files to read with estimated reading time and relevant decisions.

```
Usage: heirloom trail [OPTIONS]

Options:
  --topic TEXT       Focus the trail on a specific topic or module
  --repo TEXT        Repo ID or local path
  --max-steps INT    Maximum number of steps (default: 10)
  --json             Emit JSON output
  --markdown         Export as Markdown (stdout)
  --help             Show this message and exit.
```

**Examples**

```bash
heirloom trail
heirloom trail --topic "payment processing"
heirloom trail --max-steps 15 --markdown > onboarding.md
heirloom trail --json
```

---

## `heirloom ask <question>`

Ask a natural-language question about the repo. Answers are synthesised from recorded decisions using BM25 retrieval and the configured LLM, with citation IDs.

```
Usage: heirloom ask [OPTIONS] QUESTION

Arguments:
  QUESTION  [required]

Options:
  --repo TEXT   Repo ID or local path
  --json        Emit JSON output
  --help        Show this message and exit.
```

**Examples**

```bash
heirloom ask "Why did we switch to Stripe?"
heirloom ask "What is the retry strategy for failed webhooks?"
```

Works without an LLM: it returns the top matching decisions as a ranked, cited list, labeled "LLM not configured". With an LLM configured (see [the README](../README.md#with-keys-optional)), it writes a short answer citing decision IDs.

---

## `heirloom decide <title>`

Record a new design decision. Writes to the SQLite database and to `.heirloom/decisions/NNNN-slug.md` inside the target repo's working tree.

```
Usage: heirloom decide [OPTIONS] TITLE

Arguments:
  TITLE  [required]

Options:
  --files TEXT         Repo-relative file paths (repeatable)
  --why TEXT           The reasoning  [required]
  --alternatives TEXT  Alternatives that were considered
  --author TEXT        Override the author name
  --skill-hash TEXT    SHA-256 of the capturing skill (for auditability)
  --repo TEXT          Repo ID or local path
  --json               Emit JSON output
  --help               Show this message and exit.
```

**Examples**

```bash
heirloom decide "Use optimistic locking for inventory" \
  --files src/inventory/stock.py \
  --why "Avoids blocking reads under high concurrency; acceptable conflict rate <0.1%" \
  --alternatives "Pessimistic locking, queue-based serialisation"

heirloom decide "Migrate from Redux to Zustand" \
  --files web/src/store.ts \
  --why "Zustand has 70% less boilerplate with equal type safety" \
  --author "Bob"
```

**JSON output**
```json
{
  "id": 48,
  "record_path": ".heirloom/decisions/0048-use-optimistic-locking-for-inventory.md"
}
```

`record_path` is `null` when the repo has no local working tree (e.g. a remote clone with no checkout path).

---

## `heirloom risk`

Repo-wide at-risk report: bus-factor-1 files, inactive sole owners, and knowledge concentration by person.

```
Usage: heirloom risk [OPTIONS]

Options:
  --repo TEXT    Repo ID or local path
  --limit INT    Max at-risk files to show (default: 20)
  --json         Emit JSON output
  --help         Show this message and exit.
```

**Examples**

```bash
heirloom risk
heirloom risk --limit 50 --json
```

---

## `heirloom export`

Export the full knowledge base to stdout.

```
Usage: heirloom export [OPTIONS]

Options:
  --format TEXT   Output format: md or json (default: md)
  --repo TEXT     Repo ID or local path
  --help          Show this message and exit.
```

**Examples**

```bash
heirloom export > knowledge-base.md
heirloom export --format json > knowledge-base.json
```

---

## `heirloom serve`

Start the REST API server. When `web/dist/index.html` exists, the web UI is served with an SPA fallback so deep links work.

```
Usage: heirloom serve [OPTIONS]

Options:
  --port INT   API port (default: API_PORT env var or 8000)
  --help       Show this message and exit.
```

**Examples**

```bash
heirloom serve
heirloom serve --port 9000
```

---

## `heirloom mcp`

Start the MCP server. Default transport is stdio (for use in AI assistant MCP configs). Pass `--http` for streamable HTTP.

```
Usage: heirloom mcp [OPTIONS]

Options:
  --http        Use streamable HTTP instead of stdio
  --port INT    HTTP port (default: MCP_HTTP_PORT env var or 8765)
  --help        Show this message and exit.
```

**Examples**

```bash
heirloom mcp                   # stdio — recommended for AI assistant config
heirloom mcp --http            # HTTP on :8765
heirloom mcp --http --port 9000
```
