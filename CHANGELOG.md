# Changelog

## 0.1.0 (2026-09-27)

First release, built for the IBM Bob hackathon.

### Added
- Ingestion from a local path or a public GitHub URL: git log, blame, intent comments, docs, ADRs and (with `GITHUB_TOKEN`) merged PRs. Re-ingestion is incremental, and progress is reported through a job endpoint.
- Analysis: JS/TS/Vue/Python import graph, co-change coupling, impact sets, entry points, ownership with alias merging, bus factor and at-risk flags.
- Decision extraction with a no-key heuristic and a validated LLM path (IBM watsonx.ai Granite or any OpenAI-compatible endpoint), near-duplicate merging, and an LLM response cache.
- Why Cards, Ask Heirloom with citation enforcement, onboarding trails, BM25 decision search, and Markdown/JSON export.
- Decision capture from the web form, `heirloom decide` and the MCP tool, written to `.heirloom/decisions/` and round-tripped on re-ingest.
- REST API, Typer CLI, and a FastMCP server with seven tools and two resources.
- React web UI: Home, Repo overview with the Bus Factor Map, Why Card, Trails, Ask, Decisions and People.
- PR guard GitHub Action.
- IBM Bob integration: Archivist custom mode, `capture-why` and `onboard-me` skills, workspace MCP config.
- Docs: README, architecture, API, CLI, MCP, Bob, decisions, demo script and submission text.

### Quality
- 155 Python tests (87% coverage on `core/`), 9 web tests, ruff, mypy strict on `core/` with zero errors.
