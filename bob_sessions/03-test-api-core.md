# can you test the Fast API and Core engien of the tool

---

**Status:** active  **Date:** 2026-09-27

---

### 👤 User

can you test the Fast API and Core engien of the tool

---

### 🤖 Assistant

> 🔧 called: list_files

Let me first explore the project structure to understand what we're working with.

> 🔧 **list_files** — .

### 🤖 Assistant

> 🔧 called: list_files, list_files, list_files



> 🔧 **list_files** — tests

> 🔧 **list_files** — core

> 🔧 **list_files** — api

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — pyproject.toml

> 🔧 **read_file** — tests/conftest.py

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — tests/test_api.py

> 🔧 **read_file** — api/main.py

### 🤖 Assistant

> 🔧 called: read_file, read_file

Now let me check the existing test files and look at what the core pipeline test covers:

> 🔧 **read_file** — tests/fixtures

> 🔧 **read_file** — tests/test_pipeline.py

### 🤖 Assistant

> 🔧 called: execute_command

Now I have a good picture of the project. Let me run the existing test suite to see the current state:

> 🔧 **execute_command** — cd "c:\Users\harsh\OneDrive\Desktop\Hierloom" ; .venv\Scripts\python.exe -m pytest tests/test_api.py tests/test_pipeline.py -v --tb=short 2>&1

### 🤖 Assistant

> 🔧 called: execute_command

All 26 pass. Let me also run the full test suite to get a complete picture:

> 🔧 **execute_command** — cd "c:\Users\harsh\OneDrive\Desktop\Hierloom" ; .venv\Scripts\python.exe -m pytest --tb=short -v 2>&1

### 🤖 Assistant

**135/135 tests pass.** Here's a summary of what was tested:

---

### FastAPI Layer — [`tests/test_api.py`](tests/test_api.py) — **17 tests ✅**

| Test | What it covers |
|---|---|
| `test_health` | `GET /api/health` → `ok=True`, `llm="none"`, `demo=False` |
| `test_list_repos` | `GET /api/repos` → ingested repo present with file stats |
| `test_tree` | `GET /api/repos/{id}/tree` → `src/` appears in tree |
| `test_why_card` | `GET /api/repos/{id}/why` → summary + warnings populated |
| `test_why_card_agent_format_under_budget` | `format=agent` → response under 6 000 chars (~1 500 tokens) |
| `test_why_unknown_path_404` | 404 with `file_not_found` error code |
| `test_unknown_repo_404` | 404 with `repo_not_found` error code |
| `test_who` | `GET .../who` → bus_factor=1, at_risk=True, no emails in output |
| `test_impact` | `GET .../impact` → `src/app.py` listed, all items have reasons |
| `test_trail` + topic filter | `GET .../trail` → steps present; topic filter keeps relevant file |
| `test_ask` | `POST .../ask` → citations returned |
| `test_decisions_list_and_filter` | List + text filter on decisions |
| `test_create_decision_writes_record` | `POST .../decisions` 201 → file written to `.heirloom/decisions/` |
| `test_risk` | `GET .../risk` → `src/legacy.py` in at-risk list |
| `test_people` | `GET .../people` → names present, no emails leaked |
| `test_ingest_rejected_in_demo_mode` | `HEIRLOOM_DEMO=1` → `POST /api/repos` returns 422 |

---

### Core Engine — [`tests/test_pipeline.py`](tests/test_pipeline.py) — **9 tests ✅**

| Test | What it covers |
|---|---|
| `test_ingest_creates_files` | Files, TS, and ADO docs all ingested |
| `test_ingest_stores_commits` | Exactly 10 commits stored |
| `test_import_edges_resolved` | Py & TS import edges correctly linked |
| `test_fan_in_computed` | `fan_in ≥ 1` for `src/utils.py` |
| `test_entry_point_detected` | `src/app.py` flagged as entry point |
| `test_bus_factor_and_at_risk` | `legacy.py` → bus_factor=1, at_risk; `utils.py` → not at_risk |
| `test_decisions_extracted_with_evidence` | Heuristic extractor finds Redis decision without LLM; every decision has evidence |
| `test_adr_becomes_high_confidence_decision` | ADR → `confidence="high"` |
| `test_reingest_is_incremental_and_idempotent` | Re-ingesting same repo adds zero new rows |

The remaining **109 tests** across capture, comments, coupling, docs, export, extraction, gitlog, impact, imports, LLM providers, MCP, ownership, search/ask, trails, walker, and why-card modules all pass cleanly too — **135/135 total, 5.34 s**.