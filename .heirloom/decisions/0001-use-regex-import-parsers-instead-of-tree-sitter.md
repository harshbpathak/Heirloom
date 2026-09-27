---
id: '0001'
title: Use regex import parsers instead of tree-sitter
date: '2026-09-27'
files:
- core/analysis/imports_parser.py
confidence: high
source: manual
author: Heirloom team
skill_hash: ''
---

## Context
Import resolution has to work for JS, TS, Vue and Python.

## Decision
Use regex import parsers instead of tree-sitter

## Reasoning
Regex parsers install with zero native dependencies on every OS and cover import, require, dynamic import and from-imports, which is all the impact analysis needs.

## Alternatives considered
tree-sitter grammars: more precise, but native wheels complicate a hackathon install.
