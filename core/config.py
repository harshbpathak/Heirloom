"""Application configuration read from environment variables.

Every variable used here is documented in ``.env.example`` at the repo root.
No secrets are ever hardcoded; missing optional values degrade gracefully.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    """Read an environment variable, returning ``default`` when unset or blank."""
    value = os.environ.get(name, "")
    return value if value.strip() else default


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable (``1``/``true``/``yes`` are truthy)."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, falling back on parse errors."""
    raw = os.environ.get(name, "")
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    """Runtime settings for Heirloom, sourced from the environment."""

    heirloom_home: Path = field(
        default_factory=lambda: Path(_env("HEIRLOOM_HOME", str(Path.home() / ".heirloom"))).expanduser()
    )
    demo_mode: bool = field(default_factory=lambda: _env_bool("HEIRLOOM_DEMO"))
    log_json: bool = field(default_factory=lambda: _env_bool("HEIRLOOM_LOG_JSON"))
    max_commits: int = field(default_factory=lambda: _env_int("HEIRLOOM_MAX_COMMITS", 2000))
    api_port: int = field(default_factory=lambda: _env_int("API_PORT", 8000))
    web_port: int = field(default_factory=lambda: _env_int("WEB_PORT", 5173))
    mcp_http_port: int = field(default_factory=lambda: _env_int("MCP_HTTP_PORT", 8765))

    github_token: str = field(default_factory=lambda: _env("GITHUB_TOKEN"))

    watsonx_api_key: str = field(default_factory=lambda: _env("WATSONX_API_KEY"))
    watsonx_project_id: str = field(default_factory=lambda: _env("WATSONX_PROJECT_ID"))
    watsonx_url: str = field(
        default_factory=lambda: _env("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    )
    watsonx_model_id: str = field(
        default_factory=lambda: _env("WATSONX_MODEL_ID", "ibm/granite-3-3-8b-instruct")
    )

    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL"))

    @property
    def db_dir(self) -> Path:
        """Directory holding one SQLite database file per ingested repo."""
        return self.heirloom_home / "db"

    @property
    def cache_dir(self) -> Path:
        """Directory holding shallow clones of remote repositories."""
        return self.heirloom_home / "cache"


def get_settings() -> Settings:
    """Build a fresh :class:`Settings` from the current environment."""
    return Settings()
