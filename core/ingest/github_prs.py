"""Merged pull-request fetching from the GitHub API (spec F1 step 7).

Only runs when ``GITHUB_TOKEN`` is set and the repo source is a GitHub URL.
Without a token this module is never called; the pipeline logs the skip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

import httpx


@dataclass
class PullRequestEvidence:
    """One merged pull request as evidence."""

    number: int
    title: str
    body: str
    author: str
    merged_at: datetime | None
    url: str
    files: list[str] = field(default_factory=list)


def parse_github_source(source: str) -> tuple[str, str] | None:
    """Extract (owner, name) from a GitHub URL, or None for local paths."""
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", source.strip())
    if not match:
        return None
    return match.group(1), match.group(2)


def fetch_merged_prs(
    owner: str,
    name: str,
    token: str,
    max_prs: int = 200,
    client: httpx.Client | None = None,
) -> list[PullRequestEvidence]:
    """Fetch merged PRs (title, body, author, files) via the REST API.

    A caller-supplied ``client`` allows tests to inject a mock transport.
    """
    own_client = client is None
    http = client or httpx.Client(
        base_url="https://api.github.com",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        timeout=30,
    )
    try:
        results: list[PullRequestEvidence] = []
        page = 1
        while len(results) < max_prs:
            resp = http.get(
                f"/repos/{owner}/{name}/pulls",
                params={
                    "state": "closed",
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                },
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            for pr in batch:
                if not pr.get("merged_at"):
                    continue
                merged = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
                files = _fetch_pr_files(http, owner, name, pr["number"])
                results.append(
                    PullRequestEvidence(
                        number=pr["number"],
                        title=pr.get("title") or "",
                        body=pr.get("body") or "",
                        author=(pr.get("user") or {}).get("login", ""),
                        merged_at=merged,
                        url=pr.get("html_url") or "",
                        files=files,
                    )
                )
                if len(results) >= max_prs:
                    break
            page += 1
        return results
    finally:
        if own_client:
            http.close()


def _fetch_pr_files(http: httpx.Client, owner: str, name: str, number: int) -> list[str]:
    """List changed file paths for one PR (first 100 files)."""
    resp = http.get(f"/repos/{owner}/{name}/pulls/{number}/files", params={"per_page": 100})
    if resp.status_code != 200:
        return []
    return [f["filename"] for f in resp.json()]
