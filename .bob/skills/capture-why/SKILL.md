---
name: capture-why
description: Record the reasoning behind a code change as a Heirloom decision. Use before a commit, or when the user says "record this decision", "capture why", or "write down why we did this".
---

# capture-why

Turn the design choice in the staged changes into a durable decision record,
so the reasoning survives after the conversation ends.

## Steps

1. Run `git diff --staged --stat` and then `git diff --staged`. If nothing is
   staged, ask the user whether to use the unstaged diff (`git diff`) instead.
2. Decide whether the diff contains a **design choice**: a new approach, a
   replaced library, a changed data flow, a deliberate constraint, a workaround.
   Skip it and tell the user "No design choice to record" when the diff is only:
   - formatting, whitespace or import reordering
   - renames or moves with no behavior change (pure refactors)
   - dependency or version bumps
   - typo fixes, comment-only edits, generated files
3. Draft the decision:
   - **title**: at most 80 characters, imperative ("Use Redis for session storage").
   - **reasoning**: why this option, in 1–4 sentences. Use only what the diff,
     the conversation, or the user tells you. If the reason is unclear, ask the
     user one question rather than guessing a motive.
   - **alternatives**: what was rejected and why, or leave it out if unknown.
   - **files**: the repo-relative paths from the diff that embody the choice.
4. Compute this skill's content hash so the capture workflow version is auditable:

   ```bash
   python .bob/skills/capture-why/skill_hash.py
   ```

   It prints the SHA-256 of this `SKILL.md`.
5. Show the draft to the user and ask for a yes before writing.
6. Call the Heirloom MCP tool `record_decision` with `title`, `files`,
   `reasoning`, `alternatives` (if any), `author` (the user's name if known) and
   `skill_hash` (from step 4).
7. Report the returned `record_path` (a file under `.heirloom/decisions/`) and
   suggest staging it in the same commit so the reasoning ships with the code.

## Rules

- Never invent reasoning. An empty `alternatives` is better than a made-up one.
- One decision per distinct design choice; a diff can hold zero, one or several.
- If `record_decision` returns an `error`, show it verbatim and stop.
