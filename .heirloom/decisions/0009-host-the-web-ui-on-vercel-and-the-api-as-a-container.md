---
id: 0009
title: Host the web UI on Vercel and the API as a container
date: '2026-09-27'
files:
- Dockerfile
confidence: high
source: manual
author: Heirloom team
skill_hash: ''
---

## Context
The API needs git, writes SQLite, and runs ingestion in a background thread.

## Decision
Host the web UI on Vercel and the API as a container

## Reasoning
Serverless functions can't do those reliably, so the static UI goes on Vercel and proxies /api to a long-lived container (Render).

## Alternatives considered
API on Vercel functions: no git binary and no background work.
