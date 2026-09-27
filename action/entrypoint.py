"""GitHub Action entry point for the Heirloom PR guard (spec F10).

Runs in the Actions runner against the checked-out repo:
  1. ingest the repo (no LLM, no network beyond git),
  2. diff the PR against its base,
  3. post or update ONE comment (found by a hidden marker),
  4. optionally fail in strict mode.

On forks, ``GITHUB_TOKEN`` is read-only, so posting can fail with 403. The
report then goes to the job summary instead and the step does not fail for
that reason: the guard works on forks with no secrets.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import httpx

from core.db import session_for
from core.ingest.pipeline import ingest_repo
from core.prguard import COMMENT_MARKER, build_report, parse_changed_lines, render_comment

API = "https://api.github.com"


def _event() -> dict:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not Path(path).is_file():
        sys.exit("GITHUB_EVENT_PATH missing: this action must run on a pull_request event")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _diff(repo: Path, base_sha: str, head_sha: str) -> str:
    subprocess.run(["git", "fetch", "--no-tags", "origin", base_sha], cwd=repo, check=False)
    return subprocess.run(
        ["git", "diff", "-U0", f"{base_sha}...{head_sha}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _post_or_update(repo_full: str, number: int, body: str, token: str) -> bool:
    """Create the comment or edit the existing one. Returns False when not permitted."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    with httpx.Client(base_url=API, headers=headers, timeout=30) as http:
        existing = None
        page = 1
        while existing is None:
            resp = http.get(
                f"/repos/{repo_full}/issues/{number}/comments",
                params={"per_page": 100, "page": page},
            )
            if resp.status_code != 200 or not resp.json():
                break
            existing = next(
                (c for c in resp.json() if COMMENT_MARKER in (c.get("body") or "")), None
            )
            page += 1
        if existing:
            resp = http.patch(
                f"/repos/{repo_full}/issues/comments/{existing['id']}", json={"body": body}
            )
        else:
            resp = http.post(f"/repos/{repo_full}/issues/{number}/comments", json={"body": body})
        if resp.status_code in (401, 403, 404):
            print(
                f"::warning::Could not post PR comment ({resp.status_code}); "
                "likely a fork with a read-only token. See the job summary."
            )
            return False
        resp.raise_for_status()
        return True


def main() -> int:
    """Run the guard; the exit code is non-zero only for strict-mode failures."""
    repo = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    strict = os.environ.get("INPUT_FAIL_ON_AT_RISK", "false").lower() == "true"
    token = os.environ.get("GITHUB_TOKEN", "")
    event = _event()
    pr = event["pull_request"]

    repo_id = ingest_repo(str(repo), max_commits=int(os.environ.get("INPUT_MAX_COMMITS", "2000")))
    changed = parse_changed_lines(_diff(repo, pr["base"]["sha"], pr["head"]["sha"]))
    reviewers = [r["login"] for r in pr.get("requested_reviewers", [])]

    with session_for(repo_id) as session:
        report = build_report(session, repo_id, repo, changed, reviewers, strict=strict)
    body = render_comment(report)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(body, encoding="utf-8")
    if token:
        _post_or_update(os.environ["GITHUB_REPOSITORY"], pr["number"], body, token)
    else:
        print(body)

    for failure in report.strict_failures:
        print(f"::error::{failure}")
    return 1 if report.strict_failures else 0


if __name__ == "__main__":
    sys.exit(main())
