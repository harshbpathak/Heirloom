---
id: '0002'
title: One SQLite database per ingested repo
date: '2026-09-27'
files:
- core/db.py
confidence: high
source: manual
author: Heirloom team
skill_hash: ''
---

## Context
Each repo's analysis is independent and must be easy to ship as a demo snapshot.

## Decision
One SQLite database per ingested repo

## Reasoning
One file per repo means no server, trivial deletion, and demo snapshots that are just files in demo/.

## Alternatives considered
One shared database: harder to snapshot and to reset per repo.
