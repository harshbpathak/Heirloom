# Heirloom development targets. On Windows, run these under Git Bash or WSL,
# or copy the commands out of each target.

PY ?= .venv/Scripts/python
ifeq ($(OS),)
PY = .venv/bin/python
endif

.PHONY: install dev test lint demo web-build snapshot

install:
	python -m venv .venv || true
	$(PY) -m pip install -e ".[dev]"
	cd web && pnpm install

dev:
	$(PY) -m uvicorn api.main:app --reload --port 8000 &
	cd web && pnpm dev

test:
	$(PY) -m pytest -q
	cd web && pnpm test

lint:
	$(PY) -m ruff check core api cli mcp_server tests
	$(PY) -m ruff format --check core api cli mcp_server tests
	cd web && pnpm lint

web-build:
	cd web && pnpm install && pnpm build

demo: web-build
	HEIRLOOM_DEMO=1 HEIRLOOM_HOME=./demo $(PY) -m cli.main mcp --http &
	HEIRLOOM_DEMO=1 HEIRLOOM_HOME=./demo $(PY) -m cli.main serve --port 8000

snapshot:
	$(PY) scripts/build_demo_snapshots.py
