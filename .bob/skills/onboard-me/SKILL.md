---
name: onboard-me
description: Walk a new developer through an unfamiliar repository using Heirloom's onboarding trail. Use when the user says "onboard me", "explain this repo", "where do I start", or asks how a part of the codebase works.
---

# onboard-me

Give a guided tour of the repo in a sensible reading order instead of a file dump.

## Steps

1. Work out the topic. If the user named one ("onboard me on payments"), use it.
   Otherwise use no topic for a general trail.
2. Call the Heirloom MCP tool `onboarding_trail` with `topic` (or none) and
   `max_steps: 10`. If it returns no steps for a topic, say so and offer a
   general trail instead.
3. Show the whole trail as a numbered list: path, reading time, and the one-line
   reason for each step. Tell the user the total estimated reading time.
4. Walk through the **first 3 steps** one at a time. For each step:
   - Open the file and read it.
   - Call `ask_why(path)` and explain, in plain language:
     what the file does, the recorded decisions behind it (cite them by title),
     any `warnings` (DO NOT / HACK comments) the user must respect, and who to
     ask (from `who_knows(path)`) if the bus factor is 1.
   - Pause and ask whether they want to go deeper or move to the next step.
5. After step 3, offer the rest of the trail and stop. Do not continue unasked.

## Rules

- Explain only what the file content and Heirloom's decisions show. If Heirloom
  has no recorded reasoning for a file, say "no recorded reasoning" rather than
  guessing why it was written that way.
- Keep each step's explanation under about 150 words.
