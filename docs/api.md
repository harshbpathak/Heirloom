# Heirloom REST API Reference

The Heirloom REST API is a thin FastAPI layer over `core/`. All business logic lives in `core/`; routes validate input and delegate.

**Base URL:** `http://localhost:8000` (configurable via `API_PORT`)  
**Interactive docs:** `http://localhost:8000/api/docs`  
**OpenAPI spec:** `http://localhost:8000/api/openapi.json`

---

## Authentication

No authentication is required in the default configuration. In demo mode (`HEIRLOOM_DEMO=1`) ingestion (`POST /api/repos`) returns `422 Validation Failed`; recording decisions still works.

---

## Error format

All errors return a JSON envelope:

```json
{
  "error": {
    "code": "file_not_found",
    "message": "Path 'src/foo.py' does not exist in repo 'my-repo'."
  }
}
```

| Code | HTTP status | Meaning |
|---|---|---|
| `repo_not_found` | 404 | Repo has not been ingested |
| `file_not_found` | 404 | Path is not in the ingested repo |
| `job_not_found` | 404 | Job ID does not exist |
| `validation_failed` | 422 | Invalid request body or demo-mode write attempt |
| `ingest_error` | 400 | Ingestion failed (clone error, bad path, etc.) |
| *(other)* | 500 | Unexpected internal error |

---

## Endpoints

### `GET /api/health`

Liveness check. Returns the active LLM backend name and whether demo mode is on.

**Response**
```json
{
  "ok": true,
  "llm": "watsonx",
  "demo": false
}
```

---

### `POST /api/repos`

Start ingesting a repository. Returns immediately with IDs for polling.

**Body**
```json
{
  "source": "/path/to/repo",
  "since": "2024-01-01",
  "max_commits": 1000
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `source` | string | yes | Local filesystem path or GitHub URL |
| `since` | string | no | ISO date; only commits after this date |
| `max_commits` | integer | no | Limit on commits to process (default from `HEIRLOOM_MAX_COMMITS`) |

**Response `200`**
```json
{
  "repo_id": "my-repo",
  "job_id": "a1b2c3d4"
}
```

Poll `GET /api/jobs/{job_id}` for progress. In demo mode, `POST /api/repos` itself returns `422` because ingestion is disabled.

---

### `GET /api/repos`

List all ingested repos with their summary statistics.

**Response**
```json
[
  {
    "id": "my-repo",
    "name": "my-repo",
    "source": "/path/to/repo",
    "ingested_at": "2024-06-01T12:00:00",
    "stats": {
      "files": 312,
      "commits": 1840,
      "decisions": 47,
      "at_risk_files": 3
    }
  }
]
```

---

### `GET /api/jobs/{job_id}`

Poll the progress of an ingestion job.

**Response**
```json
{
  "id": "a1b2c3d4",
  "repo_id": "my-repo",
  "kind": "ingest",
  "status": "running",
  "progress": 65,
  "message": "Analyzing structure",
  "started_at": "2024-06-01T12:00:00",
  "finished_at": null
}
```

`status` is one of `pending`, `running`, `done`, `failed`.

---

### `GET /api/repos/{repo_id}/tree`

Nested directory/file tree for a repo with risk annotations.

**Response** (truncated)
```json
{
  "name": "",
  "type": "dir",
  "loc": 18420,
  "children": [
    {
      "name": "src",
      "type": "dir",
      "loc": 14300,
      "children": [
        {
          "name": "processor.py",
          "type": "file",
          "path": "src/payments/processor.py",
          "loc": 340,
          "bus_factor": 1,
          "at_risk": true,
          "language": "python",
          "holders": [
            { "name": "Alice", "ownership": 0.87 }
          ]
        }
      ]
    }
  ]
}
```

---

### `GET /api/repos/{repo_id}/why`

The **Why Card** for one file.

**Query params**

| Param | Default | Description |
|---|---|---|
| `path` | required | Repo-relative file path |
| `format` | `json` | Response format: `json`, `markdown`, or `agent` |

**Response (`format=json`, truncated)**
```json
{
  "path": "src/payments/processor.py",
  "language": "python",
  "loc": 340,
  "is_entry_point": false,
  "summary": "Handles charge and refund flows via Stripe.",
  "summary_source": "llm",
  "decisions": [
    {
      "id": "12",
      "title": "Switch from PayPal to Stripe",
      "reasoning": "Stripe's API is more predictable under load ...",
      "confidence": "high",
      "date": "2023-11-14",
      "evidence": [
        { "type": "pull_request", "ref": "142", "url": "https://github.com/org/repo/pull/142" }
      ]
    }
  ],
  "holders": [
    { "name": "Alice", "ownership": 0.87, "last_active": "2024-05-20", "inactive": false }
  ],
  "bus_factor": 1,
  "at_risk": false,
  "impact": [
    { "path": "tests/test_payments.py", "score": 0.91, "reason": "imports processor" }
  ],
  "warnings": [
    { "line": 88, "text": "DO NOT remove the idempotency key check — see decision #12" }
  ],
  "activity": [
    { "month": "2024-04", "commits": 3 },
    { "month": "2024-05", "commits": 1 }
  ]
}
```

**Response (`format=markdown`)** — Markdown string wrapped in `{"markdown": "..."}`.

**Response (`format=agent`)** — Compact form for AI assistants, under 1 500 tokens:
```json
{
  "path": "src/payments/processor.py",
  "summary": "Handles charge and refund flows via Stripe.",
  "decisions": [
    { "title": "Switch from PayPal to Stripe", "reasoning": "..." }
  ],
  "do_not": ["DO NOT remove the idempotency key check"],
  "impact": ["tests/test_payments.py"],
  "ask": "Alice"
}
```

---

### `GET /api/repos/{repo_id}/who`

Knowledge holders and bus factor for one file.

**Query params:** `path` (required)

**Response**
```json
{
  "path": "src/payments/processor.py",
  "holders": [
    { "name": "Alice", "ownership": 0.87, "last_active": "2024-05-20", "inactive": false },
    { "name": "Bob",   "ownership": 0.13, "last_active": "2023-09-01", "inactive": true  }
  ],
  "bus_factor": 1,
  "at_risk": false
}
```

`inactive` is `true` when the author's last commit is more than 180 days ago.  
`at_risk` is `true` when `bus_factor == 1` and the sole owner is inactive.

---

### `GET /api/repos/{repo_id}/impact`

Ranked impact set for one file.

**Query params:** `path` (required), `limit` (default 10)

**Response**
```json
{
  "path": "src/payments/processor.py",
  "impact": [
    { "path": "tests/test_payments.py", "score": 0.91, "reason": "imports processor" },
    { "path": "src/webhooks/handler.py", "score": 0.54, "reason": "co-changed 12 times" }
  ]
}
```

Score is a float in [0, 1]. Reason is human-readable. The impact set combines static import edges and historical co-change coupling.

---

### `GET /api/repos/{repo_id}/trail`

Onboarding reading trail through the repo.

**Query params:** `topic` (optional), `max_steps` (default 10)

**Response**
```json
{
  "topic": "payment processing",
  "steps": [
    {
      "path": "src/payments/processor.py",
      "reason": "Core payment logic; highest fan-in in the payments module.",
      "reading_minutes": 8,
      "decisions": [
        { "title": "Switch from PayPal to Stripe", ... }
      ]
    }
  ]
}
```

---

### `POST /api/repos/{repo_id}/ask`

Answer a natural-language question about the repo. Citations reference decision IDs.

Requires an LLM to be configured.

**Body**
```json
{ "question": "Why did we switch to Stripe?" }
```

**Response**
```json
{
  "answer": "The team switched to Stripe in November 2023 because Stripe's API ...",
  "citations": ["12", "15"]
}
```

---

### `GET /api/repos/{repo_id}/decisions`

Filterable, paginated decision list.

**Query params**

| Param | Default | Description |
|---|---|---|
| `q` | — | Free-text search over title, summary, and reasoning |
| `file` | — | Filter to decisions linked to this file path |
| `limit` | 50 | Page size |
| `offset` | 0 | Page offset |

**Response**
```json
{
  "total": 47,
  "items": [
    {
      "id": "12",
      "title": "Switch from PayPal to Stripe",
      "reasoning": "Stripe's API is more predictable under load ...",
      "confidence": "high",
      "date": "2023-11-14",
      "source": "extracted",
      "summary": "...",
      "alternatives": "PayPal, Adyen",
      "files": ["src/payments/processor.py"],
      "evidence": [
        { "type": "pull_request", "ref": "142", "url": "..." }
      ]
    }
  ]
}
```

`confidence` is one of `high`, `medium`, `low`.  
`source` is `extracted` (auto-detected from history) or `manual`.

---

### `POST /api/repos/{repo_id}/decisions`

Record a manual design decision.

**Body**
```json
{
  "title": "Use optimistic locking for inventory",
  "files": ["src/inventory/stock.py"],
  "reasoning": "Avoids blocking reads under high concurrency.",
  "alternatives": "Pessimistic locking, queue-based serialisation",
  "author": "Alice",
  "skill_hash": "abc123..."
}
```

| Field | Required | Description |
|---|---|---|
| `title` | yes | Max 80 characters |
| `files` | no | Repo-relative paths this decision touches |
| `reasoning` | yes | The reasoning behind the decision |
| `alternatives` | no | Alternatives considered |
| `author` | no | Override author name |
| `skill_hash` | no | SHA-256 of the capturing skill, for auditability |

**Response `201`**
```json
{
  "id": "48",
  "record_path": ".heirloom/decisions/0048-use-optimistic-locking-for-inventory.md"
}
```

`record_path` is `null` when the repo has no local working tree.

---

### `GET /api/repos/{repo_id}/risk`

Repo-wide risk report.

**Query params:** `limit` (default 20, max at-risk files to return)

**Response**
```json
{
  "at_risk_files": [
    { "path": "src/billing/invoice.py", "loc": 520, "bus_factor": 1 }
  ],
  "bus_factor_1_files": 8,
  "bus_factor_1_loc_pct": 14.3,
  "top_people": [
    {
      "name": "Alice",
      "owned_loc": 4200,
      "files_over_40pct": 12,
      "last_active": "2024-05-20",
      "inactive": false
    }
  ]
}
```

`bus_factor_1_loc_pct` is the percentage of total LOC owned by a single person.

---

### `GET /api/repos/{repo_id}/people`

All authors ranked by owned LOC, with concentration stats.

**Response** — same shape as `top_people` in the risk report, but all authors.
