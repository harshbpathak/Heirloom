"""Pydantic v2 schemas for Heirloom's JSON formats (spec §10)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["high", "medium", "low"]
EvidenceType = Literal["commit", "pull_request", "code_comment", "doc", "adr", "manual"]


class EvidenceRef(BaseModel):
    """A compact reference to one evidence item behind a decision."""

    type: EvidenceType
    ref: str
    url: str | None = None


class DecisionSchema(BaseModel):
    """The Decision JSON schema (spec §10.1)."""

    id: str
    title: str = Field(max_length=80)
    summary: str = ""
    reasoning: str = ""
    alternatives: str | None = None
    confidence: ConfidenceLevel = "low"
    files: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    created_at: str = ""
    source: Literal["extracted", "manual"] = "extracted"
    skill_hash: str | None = None


class ExtractedDecision(BaseModel):
    """Shape the LLM must return for one extracted decision (prompt §11.1)."""

    title: str = Field(max_length=80)
    summary: str = ""
    reasoning: str = ""
    alternatives: str | None = None
    files: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Envelope for the decision-extraction LLM response."""

    decisions: list[ExtractedDecision] = Field(default_factory=list)


class HolderSchema(BaseModel):
    """One knowledge holder on a Why Card."""

    name: str
    ownership: float
    last_active: str | None = None
    inactive: bool = False


class ImpactItem(BaseModel):
    """One entry in an impact set, with a human-readable reason."""

    path: str
    score: float
    reason: str


class WarningItem(BaseModel):
    """An intent-comment warning (e.g. ``DO NOT``, ``HACK``) with its line."""

    line: int
    text: str


class ActivityPoint(BaseModel):
    """Commits per month for the Why Card timeline."""

    month: str
    commits: int


class CompactDecision(BaseModel):
    """Decision as embedded in a Why Card (compact form)."""

    id: str
    title: str
    reasoning: str = ""
    confidence: ConfidenceLevel = "low"
    date: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class WhyCard(BaseModel):
    """The Why Card JSON (spec §10.2) — the main object of the product."""

    path: str
    language: str | None = None
    loc: int = 0
    is_entry_point: bool = False
    summary: str
    summary_source: Literal["llm", "comment", "none"] = "none"
    decisions: list[CompactDecision] = Field(default_factory=list)
    holders: list[HolderSchema] = Field(default_factory=list)
    bus_factor: int | None = None
    at_risk: bool = False
    impact: list[ImpactItem] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    activity: list[ActivityPoint] = Field(default_factory=list)


class AgentContext(BaseModel):
    """'Copy as agent context' format (spec §10.3), kept under 1500 tokens."""

    path: str
    summary: str
    decisions: list[dict[str, str]] = Field(default_factory=list)
    do_not: list[str] = Field(default_factory=list)
    impact: list[str] = Field(default_factory=list)
    ask: str | None = None


class TrailStep(BaseModel):
    """One step of an onboarding trail (spec F7)."""

    path: str
    reason: str
    decisions: list[CompactDecision] = Field(default_factory=list)
    reading_minutes: int = 1


class Trail(BaseModel):
    """An ordered reading path through the repo."""

    topic: str | None = None
    steps: list[TrailStep] = Field(default_factory=list)


class AskAnswer(BaseModel):
    """Answer envelope for Ask Heirloom (spec F8)."""

    answer: str
    citations: list[str] = Field(default_factory=list)
    route: Literal["who", "impact", "decisions", "none"] = "decisions"


class JobStatus(BaseModel):
    """Status of a background job."""

    id: str
    repo_id: str
    kind: str
    status: str
    progress: int
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
