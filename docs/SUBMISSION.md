# Heirloom: hackathon submission

## Title

Heirloom: codebase memory for people and AI agents

## One-line pitch

Heirloom tells you why code is the way it is, who still understands it, and what breaks if you change it, so knowledge does not leave when an engineer does.

## The problem

When a senior engineer leaves, the reasoning behind their code leaves with them. New developers spend days reading file trees and git logs to rebuild it. AI coding agents have the same problem: they edit code with no idea why it was written that way, and they break decisions nobody wrote down.

We measured it on a well-known open-source project. In [pallets/click](https://github.com/pallets/click), **41.7% of the 31,919 lines of code have a bus factor of 1**: a single person accounts for at least half of what survives in those files. **18 files are at risk**, meaning their only main owner has made no commit in 180 days.

## What Heirloom does

Heirloom mines git history, blame, code comments, pull requests and docs into a decision graph. On click it ingested 2,000 commits in 22 seconds and found 854 decisions, each linked to the evidence it came from.

- **Why Card:** one page per file with its decisions and evidence, knowledge holders, impact if changed, and DO NOT / HACK warnings.
- **Bus Factor Map:** a treemap colored by bus factor, with an "If this person left" view.
- **Onboarding Trails:** a reading order through the repo, general or by topic.
- **Ask Heirloom:** answers drawn only from recorded decisions, always cited.
- **Decision capture:** new decisions written as Markdown into `.heirloom/decisions/`, from the web, the CLI or an agent.
- **PR guard:** a GitHub Action that comments on every pull request with the decisions it may conflict with and the files it may break.
- **MCP server:** seven tools that give any AI agent the same memory.

## How IBM Bob is used

- **Archivist custom mode** (`.bob/custom_modes.yaml`): Bob calls `ask_why` and `impact_if_changed` before every edit, stops when a change contradicts a recorded decision, and records new decisions with `record_decision`.
- **Two skills:** `capture-why` records the design choice in a staged diff and stamps it with the SHA-256 of its own `SKILL.md`, and `onboard-me` walks a newcomer through a trail. Current hashes:
  - `capture-why`: `69c697de0420712a127ea50a0295cd84069fb230eb34c509233b808089998bb6`
  - `onboard-me`: `3f9fddbd87eea809fbdd4b2c3202a6e8a5eb9cff625523fb52df6bf5d8653a2e`
- **Bob in the build:** Bob brought `core/` to zero mypy strict errors, set up the PR guard workflow and verified it on [PR #1](https://github.com/harshbpathak/Heirloom/pull/1), and wrote the API, architecture, CLI and MCP reference docs. See [BOB.md](BOB.md) for how the work was split.
- **MCP Builder:** not used; the FastMCP server was written directly.
- **Sessions:** 4 Bob sessions, recorded in `bob_sessions/` (3 transcripts plus a task card for each). See [BOB.md](BOB.md).

## Tech stack

Python (FastAPI, SQLAlchemy, Pydantic, Typer, FastMCP, rank_bm25, rapidfuzz), IBM watsonx.ai Granite behind a provider interface, React + TypeScript + Vite + Tailwind + D3, and a GitHub Action.

## What works offline

Everything. With no API keys, decisions come from a deterministic extractor, summaries come from header comments, and Ask returns ranked, cited decisions. `HEIRLOOM_DEMO=1` never touches the network.

## Tests

155 Python tests (87% coverage on `core/`) and 9 web tests pass. `core/` passes mypy strict with zero errors.

## Links

- Repository: https://github.com/harshbpathak/Heirloom
- Demo video: _add link_
- Live demo: _add link_
