# Daksh: demo data, UI polish and remaining tasks

Shared setup, layout and team rules are in [README.md](README.md).

The tasks are in priority order. Task 1 unblocks Ayush's hosted demo, so start there.

## 1. Demo snapshots and `make demo` (spec F11)

1. Pick 3 popular, active public repos in JS/TS or Python with good commit messages and clearly different sizes. Candidates: `pallets/click` (Python), `expressjs/express` (JS) and `sindresorhus/ky` (TS). Check that each one clones and ingests cleanly.
2. Create `scripts/build_demo_snapshots.py`. The Makefile's `snapshot` target already points at it. With `HEIRLOOM_HOME=demo`, it should ingest each repo with `--max-commits 2000` and print the time each ingest takes. That timing is also the spec's "2000 commits in under 3 minutes" check, so write the numbers down.
3. **Make Why Cards work without the source files.** Demo mode doesn't ship the cloned repos, so Why Cards currently lose their warnings and fall back to "No summary available". Fix both:
   - **Summaries:** in the snapshot script, call `build_why_card` for every analyzed file while the clone still exists. It stores the summary in `files.summary`, which is reused later.
   - **Warnings:** in `core/services/whycard.py`, when `repo_path` is `None`, build warnings from the `code_comment` evidence rows instead of reading the file. Each row's `ref` is `path:line`.
4. **Fix `.gitignore`.** The databases land in `demo/db/`, but the current exception is `!demo/*.sqlite`, which doesn't match them. Change it to `!demo/db/*.sqlite`. Keep each file well under GitHub's 50 MB warning size.
5. **Make `make demo` start everything**, as the spec asks: build `web/dist`, then run `heirloom serve` and `heirloom mcp --http` together, with `HEIRLOOM_DEMO=1 HEIRLOOM_HOME=./demo`.
6. Tell whoever writes `docs/DECISIONS.md` which 3 repos you picked and why.

## 2. Make the UI good

Everything works and was checked in a browser, but it still looks like default Tailwind grey.

- **Visual identity:** a real wordmark to replace the 🏺 emoji logo, a chosen typeface, and color tokens applied consistently in both themes.
- **Loading, empty and error states on every page.** Some pages render nothing when a query fails; the Overview page is one.
- **Bus Factor Map:** show the hover tooltip next to the cursor; today it's a text line under the map. Add a keyboard-reachable alternative, such as a "riskiest files" table, because a canvas can't be tabbed through.
- **Why Card:** use a two-column layout on desktop, add score bars for impact, show initials badges for knowledge holders, and add axis labels to the activity chart.
- **Accessibility:** check WCAG 2.1 AA contrast in both themes; grey-500 text on dark backgrounds is the likely offender. Keep the text labels on every bus-factor color. Make sure every control is keyboard reachable with a visible focus ring.
- **375px width:** check every page on a phone-sized screen. The header nav must wrap, tables must scroll inside their own box, and the page must never scroll sideways.
- Keep the 9 web tests passing and add tests for new components. `pnpm lint` bans `any`.

## 3. Remaining backend tasks

- **Performance:** the spec wants Why Cards to load in under 1 second "from cache", and the map to stay smooth at 3,000 files. There's no Why Card cache yet, and impact is recomputed on every request. Measure on the largest demo repo and add caching if it's slow. For the 3,000-file check, use a big real repo or generate a synthetic one.
- **Logging:** `HEIRLOOM_LOG_JSON=1` should switch structlog to JSON output, but structlog is never configured. Configure it once at startup for the API, CLI and MCP server, and **send logs to stderr**. With stdio transport, the MCP server's stdout is the protocol channel, so any stray log line there breaks agents.
- **watsonx model id:** check the default `ibm/granite-3-3-8b-instruct` against IBM's current watsonx.ai model list, and update `core/config.py` and `.env.example` if it changed. If the team has a key, run one ingest with it to confirm the LLM path works end to end.
- **Trail reasons:** without an LLM, the step template says "defines X" using the file name. The spec wants top-level symbol names. Parse `def`, `class` and `export` names in `core/trails/builder.py`.

## Coordinate with Harsh

His Bob mypy task edits type hints across `core/`. Pull `main` after it lands before you change `whycard.py` or `builder.py`. Doing task 1 (the script and `.gitignore`) and task 2 (all in `web/`) first avoids conflicts entirely.
