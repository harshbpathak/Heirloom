"""End-to-end ingestion pipeline (spec F1) plus analysis and decision extraction.

Orchestrates: clone/open -> walk -> git log -> blame -> comments -> docs ->
PRs -> imports/coupling/ownership -> decision extraction -> SQLite.
Re-running is incremental: only commits after ``last_ingested_commit`` are
processed and only files they touched are re-blamed.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import structlog
import yaml
from sqlalchemy import delete, select

from core.analysis.coupling import compute_coupling
from core.analysis.entry_points import detect_entry_points
from core.analysis.imports_parser import resolve_imports
from core.analysis.ownership import (
    RECENT_WINDOW_DAYS,
    bus_factor,
    compute_ownership,
    is_at_risk,
    merge_identities,
)
from core.config import Settings, get_settings
from core.db import repo_id_from_source, session_for
from core.decisions.capture import load_decision_records
from core.decisions.dedupe import merge_decisions
from core.decisions.extraction import EvidenceCandidate, extract_decisions
from core.errors import IngestError
from core.ingest.blame import blame_shares
from core.ingest.comments import extract_intent_comments
from core.ingest.docs import load_docs
from core.ingest.github_prs import fetch_merged_prs, parse_github_source
from core.ingest.gitlog import default_branch, head_commit, read_git_log
from core.ingest.walker import ANALYZED_LANGUAGES, walk_repo
from core.llm.provider import get_provider
from core.models.db_models import (
    Author,
    Commit,
    CommitFile,
    Coupling,
    Decision,
    DecisionEvidence,
    DecisionFile,
    Evidence,
    File,
    Import,
    Ownership,
    Repo,
)

log = structlog.get_logger()

ProgressCallback = Callable[[int, str], None]

_STAGES = [
    (5, "Preparing repository"),
    (15, "Walking file tree"),
    (30, "Reading commit history"),
    (55, "Running git blame"),
    (65, "Extracting comments and docs"),
    (75, "Analyzing structure"),
    (90, "Extracting decisions"),
    (100, "Done"),
]


def resolve_source(source: str, settings: Settings, max_commits: int) -> Path:
    """Return a local path for the source, shallow-cloning GitHub URLs (F1.1)."""
    gh = parse_github_source(source)
    if gh is None:
        path = Path(source).expanduser().resolve()
        if not (path / ".git").exists():
            raise IngestError(f"'{source}' is not a git repository")
        return path
    owner, name = gh
    target = settings.cache_dir / f"{owner}__{name}"
    if target.exists():
        subprocess.run(["git", "fetch", "--quiet"], cwd=target, check=False)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    depth = max(max_commits + 50, 100)
    result = subprocess.run(
        ["git", "clone", "--depth", str(depth), "--no-single-branch", source, str(target)],
        capture_output=True,
    )
    if result.returncode != 0:
        raise IngestError(f"Clone failed: {result.stderr.decode(errors='replace')[:400]}")
    return target


def ingest_repo(
    source: str,
    since: str | None = None,
    max_commits: int | None = None,
    settings: Settings | None = None,
    progress: ProgressCallback | None = None,
) -> str:
    """Ingest (or incrementally re-ingest) a repo. Returns the repo id."""
    settings = settings or get_settings()
    max_commits = max_commits or settings.max_commits
    repo_id = repo_id_from_source(source)

    def report(pct: int, msg: str) -> None:
        if progress:
            progress(pct, msg)
        log.info("ingest_progress", repo=repo_id, pct=pct, msg=msg)

    report(*_STAGES[0])
    repo_path = resolve_source(source, settings, max_commits)

    with session_for(repo_id, settings.db_dir, create=True) as session:
        repo = session.get(Repo, repo_id)
        previous_head = repo.last_ingested_commit if repo else None
        if repo is None:
            repo = Repo(id=repo_id, name=repo_path.name, source=source)
            session.add(repo)
        repo.default_branch = default_branch(repo_path)

        current_head = head_commit(repo_path)
        incremental = previous_head is not None and previous_head == current_head
        if incremental:
            report(100, "Already up to date")
            return repo_id

        # ---- Walk files -------------------------------------------------
        report(*_STAGES[1])
        walked = walk_repo(repo_path)
        existing_files = {f.path: f for f in session.scalars(select(File).where(File.repo_id == repo_id))}
        walked_paths = {w.path for w in walked}
        for w in walked:
            row = existing_files.get(w.path)
            if row is None:
                row = File(repo_id=repo_id, path=w.path)
                session.add(row)
                existing_files[w.path] = row
            row.language = w.language
            row.loc = w.loc
        session.flush()
        file_ids = {path: row.id for path, row in existing_files.items()}

        # ---- Commit history ---------------------------------------------
        report(*_STAGES[2])
        after = previous_head if previous_head else None
        entries = read_git_log(repo_path, max_commits=max_commits, since=since, after_commit=after)
        known_hashes = set(session.scalars(select(Commit.hash).where(Commit.repo_id == repo_id)))
        new_entries = [e for e in entries if e.hash not in known_hashes]

        identities = merge_identities(
            [(e.author_name, e.author_email) for e in new_entries]
            + _existing_identities(session, repo_id),
            _load_alias_overrides(repo_path),
        )
        author_ids = _persist_authors(session, repo_id, identities)

        changed_paths: set[str] = set()
        for entry in new_entries:
            identity = identities.get((entry.author_name, entry.author_email))
            author_id = author_ids.get(identity.canonical_name) if identity else None
            session.add(
                Commit(hash=entry.hash, repo_id=repo_id, author_id=author_id, date=entry.date, message=entry.message)
            )
            for path, added, deleted in entry.files:
                changed_paths.add(path)
                fid = file_ids.get(path)
                if fid is not None:
                    session.merge(CommitFile(commit_hash=entry.hash, file_id=fid, added=added, deleted=deleted))
        session.flush()

        # ---- Blame (only analyzed languages; incremental = changed only) --
        report(*_STAGES[3])
        blame_targets = [
            w.path for w in walked
            if w.language in ANALYZED_LANGUAGES and (previous_head is None or w.path in changed_paths)
        ]
        blame_data: dict[str, dict[tuple[str, str], int]] = {}
        for i, path in enumerate(blame_targets):
            blame_data[path] = blame_shares(repo_path, path)
            if progress and i % 25 == 0 and blame_targets:
                pct = 30 + int(25 * (i + 1) / len(blame_targets))
                progress(pct, f"Blaming {path}")

        # ---- Comments, docs, PRs ------------------------------------------
        report(*_STAGES[4])
        comment_evidence: list[EvidenceCandidate] = []
        for w in walked:
            if w.language not in ANALYZED_LANGUAGES:
                continue
            for c in extract_intent_comments(repo_path, w.path, w.language):
                comment_evidence.append(
                    EvidenceCandidate(type="code_comment", ref=f"{c.path}:{c.line}", text=c.text, files=[c.path])
                )

        doc_evidence: list[EvidenceCandidate] = []
        for doc in load_docs(repo_path):
            doc_evidence.append(
                EvidenceCandidate(type="adr" if doc.type == "adr" else "doc", ref=doc.path, text=doc.text, files=[])
            )
        # Heirloom's own decision records round-trip as ADR evidence (F9).
        record_candidates: list[EvidenceCandidate] = []
        for rel_path, record in load_decision_records(repo_path):
            record_candidates.append(
                EvidenceCandidate(
                    type="adr",
                    ref=rel_path,
                    text=f"{record.title}\n\n{record.context}\n\n{record.reasoning}\n\nAlternatives: {record.alternatives}",
                    files=record.files,
                    date=datetime.combine(record.date, datetime.min.time()),
                )
            )

        pr_candidates: list[EvidenceCandidate] = []
        gh = parse_github_source(source)
        if gh and settings.github_token and not settings.demo_mode:
            try:
                for pr in fetch_merged_prs(gh[0], gh[1], settings.github_token):
                    pr_candidates.append(
                        EvidenceCandidate(
                            type="pull_request",
                            ref=str(pr.number),
                            text=f"{pr.title}\n{pr.body}",
                            url=pr.url,
                            date=pr.merged_at,
                            files=pr.files,
                        )
                    )
            except Exception as exc:
                log.warning("pr_fetch_failed", error=str(exc))
        elif gh:
            log.info("pr_fetch_skipped", reason="GITHUB_TOKEN not set")

        commit_candidates = [
            EvidenceCandidate(
                type="commit",
                ref=e.hash,
                text=e.message,
                date=e.date,
                files=[p for p, _, _ in e.files if p in walked_paths],
                url=_commit_url(source, e.hash),
            )
            for e in new_entries
        ]

        all_candidates = commit_candidates + pr_candidates + comment_evidence + record_candidates
        evidence_ids = _persist_evidence(session, repo_id, all_candidates + doc_evidence, author_ids={})

        # ---- Structure analysis -------------------------------------------
        report(*_STAGES[5])
        _analyze_structure(session, repo_id, repo_path, walked, file_ids)
        _analyze_coupling(session, repo_id, file_ids)
        _analyze_ownership(session, repo_id, repo_path, walked, file_ids, blame_data, identities, author_ids_by_name=author_ids)

        # ---- Decisions ------------------------------------------------------
        report(*_STAGES[6])
        provider = get_provider(settings)
        drafts = merge_decisions(extract_decisions(all_candidates, provider, session))
        _persist_decisions(session, repo_id, drafts, evidence_ids, file_ids)

        repo.last_ingested_commit = current_head
        repo.ingested_at = datetime.utcnow()
        repo.stats_json = json.dumps(_compute_stats(session, repo_id))
        report(*_STAGES[7])

    return repo_id


def _commit_url(source: str, commit_hash: str) -> str | None:
    gh = parse_github_source(source)
    if gh:
        return f"https://github.com/{gh[0]}/{gh[1]}/commit/{commit_hash}"
    return None


def _existing_identities(session, repo_id: str) -> list[tuple[str, str]]:
    """Raw (name, email) pairs already stored for this repo."""
    pairs: list[tuple[str, str]] = []
    for author in session.scalars(select(Author).where(Author.repo_id == repo_id)):
        emails = json.loads(author.emails_json)
        if emails:
            pairs.extend((author.canonical_name, e) for e in emails)
        else:
            pairs.append((author.canonical_name, ""))
    return pairs


def _load_alias_overrides(repo_path: Path) -> dict[str, str]:
    """Load ``.heirloom/authors.yml`` alias overrides (email/name -> canonical)."""
    path = repo_path / ".heirloom" / "authors.yml"
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k).lower(): str(v) for k, v in data.items()}


def _persist_authors(session, repo_id: str, identities) -> dict[str, int]:
    """Upsert canonical authors; returns canonical_name -> author id."""
    existing = {a.canonical_name: a for a in session.scalars(select(Author).where(Author.repo_id == repo_id))}
    result: dict[str, int] = {}
    for identity in {id(v): v for v in identities.values()}.values():
        row = existing.get(identity.canonical_name)
        if row is None:
            row = Author(repo_id=repo_id, canonical_name=identity.canonical_name, emails_json="[]")
            session.add(row)
            existing[identity.canonical_name] = row
        merged_emails = sorted(set(json.loads(row.emails_json)) | identity.emails)
        row.emails_json = json.dumps(merged_emails)
    session.flush()
    for name, row in existing.items():
        result[name] = row.id
    return result


def _persist_evidence(session, repo_id: str, candidates: list[EvidenceCandidate], author_ids) -> dict[str, int]:
    """Upsert evidence rows; returns 'type:ref' -> evidence id."""
    existing = {
        (e.type, e.ref): e for e in session.scalars(select(Evidence).where(Evidence.repo_id == repo_id))
    }
    for cand in candidates:
        key = (cand.type, cand.ref)
        if key in existing:
            continue
        row = Evidence(
            repo_id=repo_id, type=cand.type, ref=cand.ref, url=cand.url,
            text=cand.text[:20_000], date=cand.date,
        )
        session.add(row)
        existing[key] = row
    session.flush()
    return {f"{t}:{r}": row.id for (t, r), row in existing.items()}


def _analyze_structure(session, repo_id: str, repo_path: Path, walked, file_ids: dict[str, int]) -> None:
    """Imports, fan-in/out, entry points (F3 steps 1, 2, 5)."""
    repo_file_set = {w.path for w in walked}
    edges: set[tuple[int, int]] = set()
    fan_out: dict[str, int] = {}
    fan_in: dict[str, int] = {}
    for w in walked:
        if w.language not in ANALYZED_LANGUAGES:
            continue
        try:
            text = (repo_path / w.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        targets = resolve_imports(w.path, w.language, text, repo_file_set)
        fan_out[w.path] = len(targets)
        for t in targets:
            fan_in[t] = fan_in.get(t, 0) + 1
            if w.path in file_ids and t in file_ids:
                edges.add((file_ids[w.path], file_ids[t]))

    session.execute(delete(Import))
    for src, dst in edges:
        session.add(Import(src_file_id=src, dst_file_id=dst))

    entry_points = detect_entry_points(repo_path, sorted(repo_file_set))
    for row in session.scalars(select(File).where(File.repo_id == repo_id)):
        row.fan_in = fan_in.get(row.path, 0)
        row.fan_out = fan_out.get(row.path, 0)
        row.is_entry_point = row.path in entry_points


def _analyze_coupling(session, repo_id: str, file_ids: dict[str, int]) -> None:
    """Co-change coupling over the full stored commit history (F3 step 3)."""
    id_to_path = {v: k for k, v in file_ids.items()}
    commit_file_rows = session.execute(
        select(CommitFile.commit_hash, CommitFile.file_id).join(Commit, Commit.hash == CommitFile.commit_hash).where(Commit.repo_id == repo_id)
    ).all()
    by_commit: dict[str, list[str]] = {}
    for commit_hash, fid in commit_file_rows:
        path = id_to_path.get(fid)
        if path:
            by_commit.setdefault(commit_hash, []).append(path)

    pairs = compute_coupling(list(by_commit.values()))
    session.execute(delete(Coupling))
    for pair in pairs:
        a, b = file_ids.get(pair.file_a), file_ids.get(pair.file_b)
        if a is not None and b is not None:
            session.add(Coupling(file_a_id=a, file_b_id=b, co_changes=pair.co_changes, score=pair.score))


def _analyze_ownership(
    session, repo_id: str, repo_path: Path, walked, file_ids: dict[str, int],
    blame_data: dict[str, dict[tuple[str, str], int]], identities, author_ids_by_name: dict[str, int],
) -> None:
    """Ownership, bus factor and at-risk flags per file (F4)."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=RECENT_WINDOW_DAYS)

    # Recent lines changed and last commit date per (file, canonical author).
    rows = session.execute(
        select(CommitFile.file_id, Commit.author_id, Commit.date, CommitFile.added, CommitFile.deleted)
        .join(Commit, Commit.hash == CommitFile.commit_hash)
        .where(Commit.repo_id == repo_id)
    ).all()
    author_names = {v: k for k, v in author_ids_by_name.items()}
    recent: dict[int, dict[str, int]] = {}
    last_commit: dict[int, dict[str, datetime]] = {}
    for fid, author_id, date, added, deleted in rows:
        name = author_names.get(author_id)
        if name is None:
            continue
        prev = last_commit.setdefault(fid, {}).get(name)
        if prev is None or date > prev:
            last_commit[fid][name] = date
        if date >= cutoff:
            recent.setdefault(fid, {})[name] = recent.get(fid, {}).get(name, 0) + added + deleted

    for path, shares_raw in blame_data.items():
        fid = file_ids.get(path)
        if fid is None:
            continue
        blame_by_author: dict[str, int] = {}
        for (name, email), lines in shares_raw.items():
            identity = identities.get((name, email))
            canonical = identity.canonical_name if identity else name
            blame_by_author[canonical] = blame_by_author.get(canonical, 0) + lines

        shares = compute_ownership(blame_by_author, recent.get(fid, {}), last_commit.get(fid, {}))
        session.execute(delete(Ownership).where(Ownership.file_id == fid))
        for share in shares:
            author_id = author_ids_by_name.get(share.author)
            if author_id is None:
                author_row = Author(repo_id=repo_id, canonical_name=share.author, emails_json="[]")
                session.add(author_row)
                session.flush()
                author_ids_by_name[share.author] = author_row.id
                author_id = author_row.id
            session.add(
                Ownership(
                    file_id=fid, author_id=author_id,
                    blame_share=share.blame_share, recent_share=share.recent_share,
                    ownership=share.ownership, last_commit_at=share.last_commit_at,
                )
            )
        factor = bus_factor(shares)
        file_row = session.get(File, fid)
        file_row.bus_factor = factor
        file_row.at_risk = is_at_risk(shares, factor, now)


def _persist_decisions(session, repo_id: str, drafts, evidence_ids: dict[str, int], file_ids: dict[str, int]) -> None:
    """Insert extracted decisions, skipping ones whose evidence is already linked."""
    linked_evidence = set(session.scalars(select(DecisionEvidence.evidence_id)))
    for draft in drafts:
        eids = [evidence_ids[r] for r in draft.evidence_refs if r in evidence_ids]
        if not eids or all(e in linked_evidence for e in eids):
            continue
        decision = Decision(
            repo_id=repo_id,
            title=draft.title,
            summary=draft.summary,
            reasoning=draft.reasoning,
            alternatives=draft.alternatives,
            confidence=draft.confidence,
            created_at=draft.created_at or datetime.utcnow(),
            source="extracted",
        )
        session.add(decision)
        session.flush()
        for eid in eids:
            session.add(DecisionEvidence(decision_id=decision.id, evidence_id=eid))
            linked_evidence.add(eid)
        for path in draft.files:
            fid = file_ids.get(path)
            if fid is not None:
                session.merge(DecisionFile(decision_id=decision.id, file_id=fid))


def _compute_stats(session, repo_id: str) -> dict:
    """Repo-level stats for the overview strip."""
    files = list(session.scalars(select(File).where(File.repo_id == repo_id)))
    total_loc = sum(f.loc for f in files)
    bf1_loc = sum(f.loc for f in files if f.bus_factor == 1)
    decisions = session.scalars(select(Decision).where(Decision.repo_id == repo_id)).all()
    return {
        "files": len(files),
        "loc": total_loc,
        "decisions": len(decisions),
        "bus_factor_1_loc_pct": round(100 * bf1_loc / total_loc, 1) if total_loc else 0.0,
        "at_risk_files": sum(1 for f in files if f.at_risk),
    }
