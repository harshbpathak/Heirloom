"""Custom exception hierarchy for Heirloom.

The API layer maps these onto the ``{"error": {"code", "message"}}`` envelope.
"""

from __future__ import annotations


class HeirloomError(Exception):
    """Base class for all Heirloom errors."""

    code = "heirloom_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RepoNotFoundError(HeirloomError):
    """The requested repo id has not been ingested."""

    code = "repo_not_found"


class FileNotFoundInRepoError(HeirloomError):
    """The requested path does not exist in the ingested repo."""

    code = "file_not_found"


class IngestError(HeirloomError):
    """Something went wrong while ingesting a repository."""

    code = "ingest_error"


class JobNotFoundError(HeirloomError):
    """The requested background job id does not exist."""

    code = "job_not_found"


class LLMError(HeirloomError):
    """An LLM provider call failed; callers should fall back to heuristics."""

    code = "llm_error"


class ValidationFailedError(HeirloomError):
    """Input failed validation (bad payload, malformed decision, etc.)."""

    code = "validation_failed"
