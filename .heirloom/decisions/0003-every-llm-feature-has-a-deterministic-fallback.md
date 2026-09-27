---
id: '0003'
title: Every LLM feature has a deterministic fallback
date: '2026-09-27'
files:
- core/llm/provider.py
- core/decisions/extraction.py
confidence: high
source: manual
author: Heirloom team
skill_hash: ''
---

## Context
The whole app, including the demo, must run offline with zero API keys.

## Decision
Every LLM feature has a deterministic fallback

## Reasoning
NullProvider reports itself unavailable and each caller uses a heuristic path, so no fake LLM output can reach the UI.

## Alternatives considered
Requiring a key: blocks judges and offline use.
