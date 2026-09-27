---
id: '0004'
title: Owner activity is repo-wide, not per-file
date: '2026-09-27'
files:
- core/analysis/ownership.py
- core/ingest/pipeline.py
confidence: high
source: manual
author: Heirloom team
skill_hash: ''
---

## Context
A file's owner can be active elsewhere while not touching that file for months.

## Decision
Owner activity is repo-wide, not per-file

## Reasoning
At-risk and inactive flags use the person's latest commit anywhere in the repo; per-file activity flagged active people as risks.

## Alternatives considered
Per-file last commit: produced false at-risk flags on the fixture repo.
