"""Logging configuration for Heirloom (structlog).

Call ``configure_logging()`` once at process startup, before the first log call.
``structlog.get_logger()`` returns a lazy proxy, so modules may create loggers at
import time; configuration is applied on first use.  The API, CLI and MCP server
each call it in their entry points right after their imports.

When ``HEIRLOOM_LOG_JSON=1`` is set, all output is newline-delimited JSON
suitable for log aggregators.  Plain-text otherwise (human-readable dev mode).

**All output goes to stderr** so that the MCP server's stdout stays clean for
the JSON-RPC protocol.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(json: bool | None = None) -> None:
    """Configure structlog once.  Safe to call multiple times (idempotent).

    Args:
        json: Override the ``HEIRLOOM_LOG_JSON`` environment variable.
              Pass ``True`` to force JSON, ``False`` to force plain text,
              or leave ``None`` to read from the environment.
    """
    from core.config import get_settings

    if json is None:
        json = get_settings().log_json

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Avoid adding a second handler if called again (e.g. in tests).
    if not any(
        isinstance(h, logging.StreamHandler) and h.stream is sys.stderr for h in root.handlers
    ):
        root.addHandler(handler)
    root.setLevel(logging.INFO)
