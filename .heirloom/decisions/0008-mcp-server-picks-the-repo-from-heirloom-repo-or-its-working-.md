---
id: 0008
title: MCP server picks the repo from HEIRLOOM_REPO or its working directory
date: '2026-09-27'
files:
- mcp_server/server.py
confidence: high
source: manual
author: Heirloom team
skill_hash: ''
---

## Context
Agents launch the MCP server from the project root, often with several repos ingested.

## Decision
MCP server picks the repo from HEIRLOOM_REPO or its working directory

## Reasoning
Resolution order is HEIRLOOM_REPO, then the repo matching the working directory, then the only repo; anything ambiguous is an error, never a guess.

## Alternatives considered
Always using the first ingested repo: silently answered about the wrong repo.
