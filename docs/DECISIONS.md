# Decisions

Choices made while building Heirloom. Each one is also a record in `.heirloom/decisions/`, so Heirloom documents itself with its own tool.

- **Use regex import parsers instead of tree-sitter.** Regex parsers install with zero native dependencies on every OS and cover import, require, dynamic import and from-imports, which is all the impact analysis needs. _Rejected:_ tree-sitter grammars: more precise, but native wheels complicate a hackathon install.
- **One SQLite database per ingested repo.** One file per repo means no server, trivial deletion, and demo snapshots that are just files in demo/. _Rejected:_ One shared database: harder to snapshot and to reset per repo.
- **Every LLM feature has a deterministic fallback.** NullProvider reports itself unavailable and each caller uses a heuristic path, so no fake LLM output can reach the UI. _Rejected:_ Requiring a key: blocks judges and offline use.
- **Owner activity is repo-wide, not per-file.** At-risk and inactive flags use the person's latest commit anywhere in the repo; per-file activity flagged active people as risks. _Rejected:_ Per-file last commit: produced false at-risk flags on the fixture repo.
- **Never invent decision dates.** decisions.created_at is nullable and the UI shows 'unknown date' rather than defaulting to the ingest time. _Rejected:_ Defaulting to today: looked precise but was false.
- **Use ruff format as the formatter.** ruff format is black-compatible and runs everywhere, so CI and local checks agree. _Rejected:_ black: blocked on the team's Python version.
- **Short plain commit messages.** The team chose short plain messages ('Add PR guard action') for a readable history; AGENTS.md tells agents the same. _Rejected:_ Conventional Commits prefixes: the team found them noisy.
- **MCP server picks the repo from HEIRLOOM_REPO or its working directory.** Resolution order is HEIRLOOM_REPO, then the repo matching the working directory, then the only repo; anything ambiguous is an error, never a guess. _Rejected:_ Always using the first ingested repo: silently answered about the wrong repo.
- **Host the web UI on Vercel and the API as a container.** Serverless functions can't do those reliably, so the static UI goes on Vercel and proxies /api to a long-lived container (Render). _Rejected:_ API on Vercel functions: no git binary and no background work.

Demo repos: `pallets/click` (Python) is the measured example used in the README, submission and video.
