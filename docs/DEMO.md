# Demo script (3 minutes)

Setup: `heirloom ingest https://github.com/pallets/click` and `heirloom serve`. Have Bob open in Archivist mode on a repo you've ingested, and a PR with the Heirloom PR guard comment ready.

| Time | Show | Say |
|---|---|---|
| 0:00–0:20 | Overview page for click, Bus Factor Map. Point at the red, striped files. | "A senior engineer left. 41.7% of click's lines have a bus factor of one, and 18 files belong to someone who hasn't committed in six months." |
| 0:20–1:00 | Click `src/click/globals.py` (at risk), then `src/click/_compat.py`. Walk the Why Card: summary, decisions with commit links, knowledge holders, impact if changed. | "Every file gets a Why Card: why it's like this, who knew it, and what breaks if it changes." |
| 1:00–1:40 | Bob in Archivist mode: ask it to change a file with a recorded decision. Show Bob calling `ask_why`, finding the conflict and pausing to ask. Approve a different change; show `record_decision` and the new file in `.heirloom/decisions/`. | "The AI agent reads the history before it edits, and writes down what it decided." |
| 1:40–2:10 | Ask page: "Why does click skip the pager test on macOS?" | "Answers come only from recorded decisions, and every one is cited." |
| 2:10–2:35 | Trails page, topic "pager". Tick off three steps. | "A new developer gets a reading order, dependencies first." |
| 2:35–3:00 | The PR guard comment on the sample PR. Close on the numbers. | "It works in CI too. 155 tests, fully offline, zero API keys." |

A 90-second promo cut of the same story exists as a separate video file.
