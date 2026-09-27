---
id: '0005'
title: Never invent decision dates
date: '2026-09-27'
files:
- core/models/db_models.py
- core/ingest/pipeline.py
confidence: high
source: manual
author: Heirloom team
skill_hash: ''
---

## Context
Code comments and some docs carry no date.

## Decision
Never invent decision dates

## Reasoning
decisions.created_at is nullable and the UI shows 'unknown date' rather than defaulting to the ingest time.

## Alternatives considered
Defaulting to today: looked precise but was false.
