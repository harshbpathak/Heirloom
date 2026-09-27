# IBM Bob and Heirloom

## How Bob uses Heirloom

| File | What it is |
|---|---|
| `.bob/custom_modes.yaml` | The **Archivist** custom mode (slug `archivist`). Tool groups: read, edit, execute, mcp. Bob names the spec's "command" group `execute`. |
| `.bob/skills/capture-why/SKILL.md` | Skill that records the design choice in a staged diff. `skill_hash.py` next to it prints the SHA-256 of the `SKILL.md`, which goes into the decision's `skill_hash` front matter. |
| `.bob/skills/onboard-me/SKILL.md` | Skill that walks a newcomer through the first three steps of an onboarding trail. |
| `.bob/mcp.json` | Registers the Heirloom MCP server (`heirloom mcp`) for this workspace. |
| `AGENTS.md` | Project guidance for any agent, including calling `ask_why` before editing core modules. |

These paths come from the documentation bundled with the installed Bob extension: workspace modes in `.bob/custom_modes.yaml`, skills in `.bob/skills/<name>/SKILL.md`, and MCP servers in `.bob/mcp.json`.

To use it: activate the project's virtualenv, run `heirloom ingest .` in the target repo, then open Bob there and pick the Archivist mode.

## How the build was done

The core of Heirloom was built in Claude Code, not Bob. That covers the core library, API, CLI, MCP server, web UI, PR guard Action, and the Bob mode and skill files themselves. Bob's MCP Builder was not used; the FastMCP server in `mcp_server/` was written directly.

Bob was then used as a working team member on Heirloom's own code:

| Session | File | What Bob did | Tests added |
|---|---|---|---|
| 01 | `bob_sessions/01-mypy-strict.md` | Brought `core/` from 28 mypy strict errors to zero, in 7 commits, with no blanket `type: ignore` | 0 (all 155 existing tests kept passing) |
| 02 | `bob_sessions/02-pr-guard.md` | Added the PR guard workflow and ran it on a smoke-test PR (branch `test/pr-guard-smoke`) | 0 |
| 03 | `bob_sessions/03-docs.md` | Wrote `docs/api.md`, `docs/architecture.md`, `docs/cli.md` and `docs/mcp.md` | 0 |

Session files are exported from Bob into `bob_sessions/`. Rows without a matching file mean that session hasn't been exported yet.
