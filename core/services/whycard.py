"""Why Card assembly (spec F5) and the compact agent-context format (§10.3)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import LLMError
from core.ingest.comments import WARNING_MARKERS, extract_intent_comments
from core.llm.prompts_loader import load_prompt
from core.llm.provider import LLMProvider, cached_complete_json
from core.models.db_models import Evidence, File
from core.models.schemas import ActivityPoint, AgentContext, CompactDecision, WarningItem, WhyCard
from core.services.queries import (
    activity_for_file,
    decisions_for_file,
    get_file_or_raise,
    holders_for_file,
    impact_for_file,
)

MAX_AGENT_CONTEXT_CHARS = 5200  # ~1300 tokens, keeps §10.3's 1500-token budget


def build_why_card(
    session: Session,
    repo_id: str,
    path: str,
    repo_path: Path | None = None,
    provider: LLMProvider | None = None,
) -> WhyCard:
    """Assemble the Why Card for one file."""
    file_row = get_file_or_raise(session, repo_id, path)
    decisions = decisions_for_file(session, repo_id, path)
    holders = holders_for_file(session, file_row)
    impact = impact_for_file(session, repo_id, path, limit=10)
    warnings = (
        _warnings(repo_path, path, file_row.language)
        if repo_path
        else _warnings_from_evidence(session, file_row)
    )
    activity = [ActivityPoint(**a) for a in activity_for_file(session, file_row)]

    summary, summary_source = _summary(session, file_row, repo_path, provider, decisions)
    if file_row.summary != summary:
        file_row.summary = summary
        file_row.summary_source = summary_source
        session.flush()

    return WhyCard(
        path=file_row.path,
        language=file_row.language,
        loc=file_row.loc,
        is_entry_point=file_row.is_entry_point,
        summary=summary,
        summary_source=summary_source,  # type: ignore[arg-type]
        decisions=decisions,
        holders=holders,
        bus_factor=file_row.bus_factor,
        at_risk=file_row.at_risk,
        impact=impact,
        warnings=warnings,
        activity=activity,
    )


def _warnings(repo_path: Path, path: str, language: str | None) -> list[WarningItem]:
    """Warning-grade intent comments (DO NOT, HACK, ...) in the file."""
    return [
        WarningItem(line=c.line, text=c.text)
        for c in extract_intent_comments(repo_path, path, language)
        if c.is_warning
    ]


def _warnings_from_evidence(session: Session, file_row: File) -> list[WarningItem]:
    """Rebuild warnings from stored code_comment evidence when the source is absent.

    Each code_comment evidence row has ``ref = "path:line"`` and ``text`` is the
    comment text. We filter to warning-grade markers so the result matches what
    ``_warnings`` would return when the file is present.
    """
    # Collect evidence ids linked to decisions that touch this file, then also
    # grab all code_comment evidence whose ref starts with this file's path.
    # The simplest approach: query all code_comment evidence for the repo whose
    # ref starts with "<path>:" — no join needed.
    prefix = f"{file_row.path}:"
    rows = session.scalars(
        select(Evidence).where(
            Evidence.repo_id == file_row.repo_id,
            Evidence.type == "code_comment",
            Evidence.ref.like(f"{file_row.path}:%"),
        )
    ).all()
    result: list[WarningItem] = []
    for ev in rows:
        upper = ev.text.upper()
        if not any(marker in upper for marker in WARNING_MARKERS):
            continue
        # ref is "path:line"
        ref_suffix = ev.ref[len(prefix) :]
        try:
            line = int(ref_suffix)
        except ValueError:
            line = 0
        result.append(WarningItem(line=line, text=ev.text[:500]))
    return result


def _summary(
    session: Session,
    file_row: File,
    repo_path: Path | None,
    provider: LLMProvider | None,
    decisions: list[CompactDecision],
) -> tuple[str, str]:
    """File summary: cached, LLM if available, else header comment, else honest 'none'."""
    if file_row.summary and file_row.summary_source != "none":
        return file_row.summary, file_row.summary_source

    text = ""
    if repo_path is not None:
        try:
            text = (repo_path / file_row.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""

    if provider is not None and provider.available and text:
        try:
            payload = json.dumps(
                {
                    "path": file_row.path,
                    "content": text[:6000],
                    "decisions": [d.title for d in decisions[:5]],
                }
            )
            raw = cached_complete_json(provider, session, load_prompt("file_summary"), payload)
            summary = str(raw.get("summary", "")).strip()
            if summary:
                return summary[:600], "llm"
        except LLMError:
            pass

    header = _header_comment(text, file_row.language)
    if header:
        return header[:600], "comment"
    return "No summary available (no LLM configured and no header comment)", "none"


def _header_comment(text: str, language: str | None) -> str | None:
    """First docstring or header comment of a file, if any."""
    if not text:
        return None
    if language == "python":
        match = re.match(r'\s*(?:#[^\n]*\n)*\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', text, re.DOTALL)
        if match:
            return " ".join(match.group(1).split())
        hash_lines = re.match(r"\s*((?:#[^\n]*\n)+)", text)
        if hash_lines:
            cleaned = " ".join(
                line.lstrip("#!").strip()
                for line in hash_lines.group(1).splitlines()
                if not line.startswith("#!")
            ).strip()
            return cleaned or None
    if language in ("javascript", "typescript", "vue"):
        block = re.match(r"\s*/\*+(.*?)\*/", text, re.DOTALL)
        if block:
            cleaned = " ".join(part.strip(" *") for part in block.group(1).splitlines())
            return " ".join(cleaned.split()) or None
        lines = re.match(r"\s*((?://[^\n]*\n)+)", text)
        if lines:
            return (
                " ".join(line.lstrip("/ ").strip() for line in lines.group(1).splitlines()).strip()
                or None
            )
    return None


def agent_context(card: WhyCard) -> AgentContext:
    """The compact 'Copy as agent context' JSON, kept under 1500 tokens."""
    ctx = AgentContext(
        path=card.path,
        summary=card.summary,
        decisions=[{"title": d.title, "reasoning": d.reasoning[:300]} for d in card.decisions[:8]],
        do_not=[w.text[:200] for w in card.warnings[:8]],
        impact=[i.path for i in card.impact[:10]],
        ask=card.holders[0].name if card.holders else None,
    )
    # Enforce the token budget by trimming decisions, then impact.
    while len(ctx.model_dump_json()) > MAX_AGENT_CONTEXT_CHARS and ctx.decisions:
        ctx.decisions.pop()
    while len(ctx.model_dump_json()) > MAX_AGENT_CONTEXT_CHARS and ctx.impact:
        ctx.impact.pop()
    return ctx


def why_card_markdown(card: WhyCard) -> str:
    """Render a Why Card as Markdown ('Copy as Markdown', MCP resource)."""
    lines = [f"# Why Card: {card.path}", ""]
    badges = [card.language or "unknown language", f"{card.loc} LOC"]
    if card.is_entry_point:
        badges.append("entry point")
    if card.bus_factor is not None:
        badges.append(f"bus factor {card.bus_factor}")
    if card.at_risk:
        badges.append("AT RISK")
    lines += [" · ".join(badges), "", f"**Summary** ({card.summary_source}): {card.summary}", ""]

    lines.append("## Why it is like this")
    if card.decisions:
        for d in card.decisions:
            refs = ", ".join(e.ref for e in d.evidence[:3])
            lines.append(
                f"- **{d.title}** ({d.confidence}, {d.date or 'unknown date'}) — {d.reasoning[:200]} [{refs}]"
            )
    else:
        lines.append("- No recorded decisions for this file.")

    lines += ["", "## Knowledge holders"]
    if card.holders:
        for h in card.holders:
            tag = " (inactive)" if h.inactive else ""
            lines.append(
                f"- {h.name}: {h.ownership:.0%}, last active {h.last_active or 'unknown'}{tag}"
            )
    else:
        lines.append("- unknown (no blame data for this file)")

    lines += ["", "## Impact if changed"]
    if card.impact:
        for i in card.impact:
            lines.append(f"- {i.path} (score {i.score:.2f}): {i.reason}")
    else:
        lines.append("- No known dependents.")

    if card.warnings:
        lines += ["", "## Warnings"]
        for w in card.warnings:
            lines.append(f"- line {w.line}: {w.text}")

    return "\n".join(lines) + "\n"
