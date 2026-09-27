# Heirloom MCP Server Reference

The Heirloom MCP server ([Model Context Protocol](https://modelcontextprotocol.io)) lets AI coding assistants call Heirloom directly from inside a conversation. It exposes 7 tools and 2 resources, all backed by the same `core/` library as the CLI and REST API.

---

## Setup

### stdio transport (recommended)

Add to your AI assistant's MCP configuration:

```json
{
  "mcpServers": {
    "heirloom": {
      "command": "heirloom",
      "args": ["mcp"]
    }
  }
}
```

### Streamable HTTP transport

Start the server manually:

```bash
heirloom mcp --http           # listens on MCP_HTTP_PORT (default 8765)
heirloom mcp --http --port 9000
```

Then configure your assistant with:

```json
{
  "mcpServers": {
    "heirloom": {
      "url": "http://localhost:8765/mcp"
    }
  }
}
```

### Prerequisites

Before the MCP server can answer queries, at least one repo must be ingested:

```bash
heirloom ingest /path/to/your/repo
```

---

## Repo resolution

When `repo_id` is not supplied to a tool, the server picks the target repo in this order:

1. `HEIRLOOM_REPO` environment variable (set it to a local path or repo ID).
2. The repo whose ID matches the server's current working directory (most AI assistants launch the MCP server from the project root).
3. The sole ingested repo.

If none of these match and multiple repos are ingested, the call returns an error asking you to pass `repo_id` explicitly or set `HEIRLOOM_REPO`.

---

## Response size budget

Every tool response is capped at approximately 2 000 tokens (~8 000 characters). When a list would exceed this limit, items are trimmed from the end and a `truncated` field is added:

```json
{
  "truncated": "3 items cut to stay under the response size limit"
}
```

---

## Tools

### `ask_why`

Returns the **Why Card** for a file. Call this before editing any file you are not already familiar with.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Repo-relative file path |
| `symbol` | string | no | Reserved for future symbol-level cards |
| `repo_id` | string | no | Repo ID (auto-resolved when omitted) |

**Response**
```json
{
  "path": "src/payments/processor.py",
  "summary": "Handles charge and refund flows via Stripe.",
  "summary_source": "llm",
  "decisions": [
    {
      "id": "12",
      "title": "Switch from PayPal to Stripe",
      "reasoning": "Stripe's API is more predictable under load ...",
      "confidence": "high",
      "evidence": ["pull_request:142"]
    }
  ],
  "warnings": [
    { "line": 88, "text": "DO NOT remove the idempotency key check" }
  ],
  "bus_factor": 1,
  "at_risk": false
}
```

`summary_source` is one of `llm`, `comment` (extracted from the file header), or `none`.  
`confidence` is one of `high`, `medium`, `low`.

---

### `who_knows`

Knowledge holders for a file: who owns it, when they were last active, and whether the file is at risk.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Repo-relative file path |
| `repo_id` | string | no | Repo ID |

**Response**
```json
{
  "path": "src/payments/processor.py",
  "holders": [
    {
      "name": "Alice",
      "ownership": 0.87,
      "last_active": "2024-05-20",
      "inactive": false
    },
    {
      "name": "Bob",
      "ownership": 0.13,
      "last_active": "2023-09-01",
      "inactive": true
    }
  ],
  "bus_factor": 1,
  "at_risk": false
}
```

`ownership` is a float in [0, 1] representing the author's share of current lines.  
`inactive` is `true` when the author's last commit is more than 180 days ago.  
`at_risk` is `true` when `bus_factor == 1` and the sole owner is inactive.

---

### `impact_if_changed`

Ranked list of files most likely to break if a given file changes. Combines static import edges and historical co-change coupling.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Repo-relative file path |
| `limit` | integer | no | Max results (default 10) |
| `repo_id` | string | no | Repo ID |

**Response**
```json
{
  "path": "src/payments/processor.py",
  "impact": [
    {
      "path": "tests/test_payments.py",
      "score": 0.91,
      "reason": "imports processor"
    },
    {
      "path": "src/webhooks/handler.py",
      "score": 0.54,
      "reason": "co-changed 12 times"
    }
  ]
}
```

`score` is a float in [0, 1]; higher means more likely to be affected.

---

### `onboarding_trail`

Ordered reading path through the repo for a new developer. Ranks files by entry-point score and fan-in; uses the LLM (if available) to rerank and filter by topic.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `topic` | string | no | Focus the trail on a topic, module, or feature |
| `max_steps` | integer | no | Maximum steps (default 10) |
| `repo_id` | string | no | Repo ID |

**Response**
```json
{
  "topic": "payment processing",
  "steps": [
    {
      "path": "src/payments/processor.py",
      "reason": "Core payment logic; highest fan-in in the module.",
      "reading_minutes": 8,
      "decisions": ["Switch from PayPal to Stripe"]
    },
    {
      "path": "src/payments/webhook.py",
      "reason": "Handles async payment events from Stripe.",
      "reading_minutes": 5,
      "decisions": []
    }
  ]
}
```

---

### `search_decisions`

Full-text BM25 search over all recorded decisions (titles, reasoning, and evidence text).

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | Search query |
| `limit` | integer | no | Max results (default 8) |
| `repo_id` | string | no | Repo ID |

**Response**
```json
{
  "query": "payment gateway",
  "decisions": [
    {
      "id": "12",
      "title": "Switch from PayPal to Stripe",
      "reasoning": "Stripe's API is more predictable ...",
      "confidence": "high",
      "date": "2023-11-14",
      "evidence": [
        { "type": "pull_request", "ref": "142", "url": "..." }
      ]
    }
  ]
}
```

---

### `record_decision`

Persist a new design decision. Writes to Heirloom's SQLite database and to `.heirloom/decisions/NNNN-slug.md` inside the target repo's working tree. Use this after making a real design choice so future developers can find the reasoning.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `title` | string | yes | Short decision title (max 80 chars) |
| `files` | array of strings | yes | Repo-relative paths this decision touches |
| `reasoning` | string | yes | The reasoning behind the decision |
| `alternatives` | string | no | Alternatives that were considered |
| `author` | string | no | Override the author name |
| `skill_hash` | string | no | SHA-256 of the capturing skill (stored in front matter for auditability) |
| `repo_id` | string | no | Repo ID |

**Response**
```json
{
  "id": "48",
  "record_path": ".heirloom/decisions/0048-use-optimistic-locking.md"
}
```

`record_path` is `null` when there is no local working tree for the repo.

---

### `repo_risk_report`

Repo-wide view of at-risk files and knowledge concentration by person.

**Parameters**

| Name | Type | Required | Description |
|---|---|---|---|
| `limit` | integer | no | Max at-risk files to return (default 20) |
| `repo_id` | string | no | Repo ID |

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

---

## Resources

Resources are readable URIs exposed via the MCP protocol, addressable as context by the AI assistant.

### `heirloom://repo/{repo_id}/why/{path*}`

The Why Card for a file, rendered as Markdown. The `{path*}` wildcard matches paths with slashes (e.g. `src/payments/processor.py`).

**Example URI:** `heirloom://repo/my-repo/why/src/payments/processor.py`

**Returns:** Markdown string with sections for summary, decisions, knowledge holders, impact, and warnings.

---

### `heirloom://repo/{repo_id}/decisions`

Index of all recorded decisions for a repo, in reverse chronological order.

**Example URI:** `heirloom://repo/my-repo/decisions`

**Returns:** Markdown list:
```markdown
# Decisions in my-repo

- [12] Switch from PayPal to Stripe (high, extracted)
- [11] Adopt optimistic locking for inventory (medium, manual)
```

---

## Recommended usage pattern

1. **Before editing a file:** call `ask_why` to read the Why Card — decisions, warnings, and who to ask.
2. **To understand ripple effects:** call `impact_if_changed` to see which other files will need updating.
3. **After making a design choice:** call `record_decision` to persist the reasoning so the next developer doesn't have to re-discover it.
4. **To find existing precedent:** call `search_decisions` before re-implementing something that may already have a recorded rationale.
