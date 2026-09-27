"""LLM provider interface with watsonx, OpenAI-compatible and Null backends.

Every feature that calls an LLM has a deterministic fallback, so the whole
app runs offline with zero keys (spec rule 4). Responses are cached in
SQLite keyed by a hash of prompt + input (spec §11).
"""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from core.config import Settings, get_settings
from core.errors import LLMError
from core.timeutil import utcnow


class LLMProvider(ABC):
    """Interface all LLM backends implement."""

    name = "abstract"

    @property
    def available(self) -> bool:
        """Whether this provider can actually make calls."""
        return True

    @abstractmethod
    def complete_text(self, prompt: str) -> str:
        """Return a plain-text completion for a prompt."""

    def complete_json(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return a parsed JSON completion; raises :class:`LLMError` on bad JSON."""
        raw = self.complete_text(prompt)
        return parse_json_response(raw)


class NullProvider(LLMProvider):
    """Deterministic no-op provider used when no API key is configured.

    Callers must check :attr:`available` and use their heuristic fallback;
    calling it anyway raises so silent fake output can never leak into the UI.
    """

    name = "none"

    @property
    def available(self) -> bool:
        return False

    def complete_text(self, prompt: str) -> str:
        raise LLMError("No LLM configured (NullProvider); use the heuristic fallback")


class WatsonxProvider(LLMProvider):
    """IBM watsonx.ai backend using a Granite instruct model."""

    name = "watsonx"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any = None

    @property
    def available(self) -> bool:
        return bool(self._settings.watsonx_api_key and self._settings.watsonx_project_id)

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from ibm_watsonx_ai import Credentials  # type: ignore[import-not-found]
                from ibm_watsonx_ai.foundation_models import (
                    ModelInference,  # type: ignore[import-not-found]
                )
            except ImportError as exc:
                raise LLMError(
                    "ibm-watsonx-ai is not installed; install with `pip install heirloom[watsonx]`"
                ) from exc
            credentials = Credentials(
                url=self._settings.watsonx_url, api_key=self._settings.watsonx_api_key
            )
            self._model = ModelInference(
                model_id=self._settings.watsonx_model_id,
                credentials=credentials,
                project_id=self._settings.watsonx_project_id,
                params={"max_new_tokens": 2000, "temperature": 0.0},
            )
        return self._model

    def complete_text(self, prompt: str) -> str:
        try:
            result = self._get_model().generate_text(prompt=prompt)
        except Exception as exc:  # SDK raises many exception types
            raise LLMError(f"watsonx call failed: {exc}") from exc
        return str(result)


class OpenAICompatibleProvider(LLMProvider):
    """Any OpenAI-compatible chat endpoint via LLM_BASE_URL/LLM_API_KEY."""

    name = "openai-compatible"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def available(self) -> bool:
        return bool(self._settings.llm_base_url)

    def complete_text(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self._settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self._settings.llm_api_key}"
        try:
            resp = httpx.post(
                self._settings.llm_base_url.rstrip("/") + "/chat/completions",
                headers=headers,
                json={
                    "model": self._settings.llm_model or "default",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
                timeout=120,
            )
            resp.raise_for_status()
            return str(resp.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise LLMError(f"OpenAI-compatible call failed: {exc}") from exc


def parse_json_response(raw: str) -> dict[str, Any]:
    """Parse JSON from a model response, tolerating markdown code fences."""
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model returned invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("Model returned JSON that is not an object")
    return parsed


def get_provider(settings: Settings | None = None) -> LLMProvider:
    """Pick the configured provider: watsonx, then OpenAI-compatible, else Null."""
    settings = settings or get_settings()
    if settings.demo_mode:
        return NullProvider()
    watsonx = WatsonxProvider(settings)
    if watsonx.available:
        return watsonx
    openai_compat = OpenAICompatibleProvider(settings)
    if openai_compat.available:
        return openai_compat
    return NullProvider()


def cache_key(prompt: str, payload: str) -> str:
    """Stable cache key: SHA-256 of prompt + input."""
    return hashlib.sha256((prompt + "\x00" + payload).encode("utf-8")).hexdigest()


def cached_complete_json(
    provider: LLMProvider,
    session: Any,
    prompt: str,
    payload: str,
) -> dict[str, Any]:
    """complete_json with a SQLite-backed cache so re-runs cost nothing."""
    from core.models.db_models import LLMCache

    key = cache_key(prompt, payload)
    hit = session.get(LLMCache, key)
    if hit is not None:
        result = json.loads(hit.response)
        assert isinstance(result, dict)
        return result
    result = provider.complete_json(prompt + "\n\n" + payload)
    session.add(LLMCache(key=key, response=json.dumps(result), created_at=utcnow()))
    return result
