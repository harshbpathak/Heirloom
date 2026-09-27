---
id: '0006'
title: Use ruff format as the formatter
date: '2026-09-27'
files:
- pyproject.toml
confidence: high
source: manual
author: Heirloom team
skill_hash: ''
---

## Context
The spec asks for black, but black refuses to run on Python 3.12.5 (an upstream safety check).

## Decision
Use ruff format as the formatter

## Reasoning
ruff format is black-compatible and runs everywhere, so CI and local checks agree.

## Alternatives considered
black: blocked on the team's Python version.
