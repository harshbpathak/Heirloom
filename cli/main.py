"""Heirloom CLI (spec F12), built with Typer and rich."""

from __future__ import annotations

import json as jsonlib
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from core.config import get_settings
from core.db import list_repo_ids, repo_id_from_source, session_for
from core.errors import HeirloomError
from core.llm.provider import get_provider

app = typer.Typer(
    name="heirloom",
    help="Why code is the way it is, who understands it, what breaks if you change it.",
)
console = Console()


def _resolve_repo(repo: str | None) -> str:
    """Resolve --repo (id or path) to a repo id; default to the sole ingested repo."""
    if repo:
        if Path(repo).exists():
            return repo_id_from_source(repo)
        return repo
    ids = list_repo_ids()
    if len(ids) == 1:
        return ids[0]
    if not ids:
        raise HeirloomError("No repos ingested yet. Run `heirloom ingest <path-or-url>` first.")
    raise HeirloomError(f"Multiple repos ingested ({', '.join(ids)}); pass --repo <id>.")


def _output(data: object, as_json: bool) -> bool:
    """Print JSON when requested; returns True when handled."""
    if as_json:
        console.print_json(jsonlib.dumps(data, default=str))
        return True
    return False


@app.command()
def ingest(
    source: str = typer.Argument(..., help="Local path or public GitHub URL"),
    since: str | None = typer.Option(None, help="Only commits after this date"),
    max_commits: int | None = typer.Option(None, help="Commit limit (default 2000)"),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Ingest a repository: history, blame, comments, docs, analysis, decisions."""
    from core.ingest.pipeline import ingest_repo

    with Progress(console=console, transient=True) as progress:
        task = progress.add_task("Ingesting", total=100)

        def report(pct: int, msg: str) -> None:
            progress.update(task, completed=pct, description=msg[:40])

        repo_id = ingest_repo(source, since=since, max_commits=max_commits, progress=report)

    with session_for(repo_id) as session:
        from core.services.queries import repo_stats

        stats = repo_stats(session, repo_id)
    if _output({"repo_id": repo_id, "stats": stats}, json):
        return
    console.print(
        f"[green]Ingested[/green] {repo_id}: {stats.get('files', 0)} files, "
        f"{stats.get('decisions', 0)} decisions, {stats.get('at_risk_files', 0)} at-risk files"
    )


@app.command()
def why(
    file: str = typer.Argument(..., help="Repo-relative file path"),
    repo: str | None = typer.Option(None, "--repo"),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Print the Why Card for a file."""
    from core.services.capture_service import local_repo_path
    from core.services.whycard import build_why_card, why_card_markdown

    repo_id = _resolve_repo(repo)
    with session_for(repo_id) as session:
        card = build_why_card(
            session,
            repo_id,
            file,
            repo_path=local_repo_path(session, repo_id),
            provider=get_provider(),
        )
    if _output(card.model_dump(), json):
        return
    from rich.markdown import Markdown

    console.print(Markdown(why_card_markdown(card)))


@app.command()
def who(
    path: str = typer.Argument(..., help="File or directory"),
    repo: str | None = typer.Option(None, "--repo"),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Knowledge holders and bus factor for a file or directory."""
    from sqlalchemy import select

    from core.models.db_models import File
    from core.services.queries import get_file_or_raise, holders_for_file

    repo_id = _resolve_repo(repo)
    with session_for(repo_id) as session:
        exact = session.scalar(select(File).where(File.repo_id == repo_id, File.path == path))
        rows = (
            [exact]
            if exact
            else list(
                session.scalars(
                    select(File).where(
                        File.repo_id == repo_id, File.path.like(f"{path.rstrip('/')}/%")
                    )
                )
            )
        )
        if not rows:
            get_file_or_raise(session, repo_id, path)  # raises with a clear message
        result = []
        for row in rows:
            holders = holders_for_file(session, row)
            result.append(
                {
                    "path": row.path,
                    "bus_factor": row.bus_factor,
                    "at_risk": row.at_risk,
                    "holders": [h.model_dump() for h in holders],
                }
            )
    if _output(result, json):
        return
    table = Table(title=f"Knowledge holders: {path}")
    table.add_column("File")
    table.add_column("Bus factor")
    table.add_column("Holders")
    for item in result:
        holders_text = (
            ", ".join(
                f"{h['name']} {h['ownership']:.0%}{' (inactive)' if h['inactive'] else ''}"
                for h in item["holders"]
            )
            or "unknown (no blame data)"
        )
        bf = str(item["bus_factor"]) if item["bus_factor"] is not None else "unknown"
        if item["at_risk"]:
            bf += " [red]AT RISK[/red]"
        table.add_row(item["path"], bf, holders_text)
    console.print(table)


@app.command()
def impact(
    file: str = typer.Argument(...),
    repo: str | None = typer.Option(None, "--repo"),
    limit: int = typer.Option(10),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Files likely affected if this file changes, with reasons."""
    from core.services.queries import impact_for_file

    repo_id = _resolve_repo(repo)
    with session_for(repo_id) as session:
        items = impact_for_file(session, repo_id, file, limit)
    if _output([i.model_dump() for i in items], json):
        return
    if not items:
        console.print(f"No known dependents of {file}.")
        return
    table = Table(title=f"Impact if {file} changes")
    table.add_column("File")
    table.add_column("Score")
    table.add_column("Reason")
    for i in items:
        table.add_row(i.path, f"{i.score:.2f}", i.reason)
    console.print(table)


@app.command()
def trail(
    topic: str | None = typer.Option(None, "--topic"),
    repo: str | None = typer.Option(None, "--repo"),
    max_steps: int = typer.Option(10),
    json: bool = typer.Option(False, "--json"),
    markdown: bool = typer.Option(False, "--markdown", help="Export as Markdown"),
) -> None:
    """Generate an onboarding reading trail."""
    from core.services.capture_service import local_repo_path
    from core.trails.builder import build_trail

    repo_id = _resolve_repo(repo)
    with session_for(repo_id) as session:
        result = build_trail(
            session,
            repo_id,
            topic=topic,
            max_steps=max_steps,
            repo_path=local_repo_path(session, repo_id),
            provider=get_provider(),
        )
    if _output(result.model_dump(), json):
        return
    title = f"Onboarding trail{f': {topic}' if topic else ''}"
    if markdown:
        lines = [f"# {title}", ""]
        for n, step in enumerate(result.steps, 1):
            lines.append(f"{n}. **{step.path}** (~{step.reading_minutes} min) — {step.reason}")
        console.print("\n".join(lines))
        return
    console.print(f"[bold]{title}[/bold]")
    for n, step in enumerate(result.steps, 1):
        console.print(f"  {n}. [cyan]{step.path}[/cyan] (~{step.reading_minutes} min)")
        console.print(f"     {step.reason}")
        for d in step.decisions:
            console.print(f"     [dim]decision:[/dim] {d.title}")


@app.command()
def ask(
    question: str = typer.Argument(...),
    repo: str | None = typer.Option(None, "--repo"),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Ask a question about the repo; answers cite recorded decisions."""
    from core.services.ask import ask as ask_service

    repo_id = _resolve_repo(repo)
    with session_for(repo_id) as session:
        answer = ask_service(session, repo_id, question, get_provider())
    if _output(answer.model_dump(), json):
        return
    console.print(answer.answer)
    if answer.citations:
        console.print(f"[dim]Citations: {', '.join(answer.citations)}[/dim]")


@app.command()
def decide(
    title: str = typer.Argument(...),
    files: list[str] = typer.Option([], "--files"),
    why_text: str = typer.Option(..., "--why", help="The reasoning"),
    alternatives: str | None = typer.Option(None, "--alternatives"),
    author: str | None = typer.Option(None, "--author"),
    skill_hash: str | None = typer.Option(
        None, "--skill-hash", help="SHA-256 of the capturing skill"
    ),
    repo: str | None = typer.Option(None, "--repo"),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Record a new decision (CLI entry point of F9)."""
    from core.services.capture_service import local_repo_path, record_decision

    repo_id = _resolve_repo(repo)
    with session_for(repo_id) as session:
        decision_id, record_path = record_decision(
            session,
            repo_id,
            title,
            files,
            why_text,
            alternatives=alternatives,
            author=author,
            skill_hash=skill_hash,
            repo_path=local_repo_path(session, repo_id),
        )
    if _output({"id": decision_id, "record_path": record_path}, json):
        return
    console.print(
        f"[green]Recorded decision {decision_id}[/green]"
        + (f" -> {record_path}" if record_path else " (SQLite only; no working tree)")
    )


@app.command()
def risk(
    repo: str | None = typer.Option(None, "--repo"),
    limit: int = typer.Option(20),
    json: bool = typer.Option(False, "--json"),
) -> None:
    """Repo-wide at-risk report."""
    from core.services.queries import risk_report

    repo_id = _resolve_repo(repo)
    with session_for(repo_id) as session:
        report = risk_report(session, repo_id, limit)
    if _output(report, json):
        return
    console.print(f"[bold]Risk report: {repo_id}[/bold]")
    console.print(
        f"  {report['bus_factor_1_loc_pct']}% of LOC has bus factor 1 "
        f"({report['bus_factor_1_files']} files)"
    )
    if report["at_risk_files"]:
        table = Table(title="At-risk files (bus factor 1, owner inactive)")
        table.add_column("File")
        table.add_column("LOC")
        for f in report["at_risk_files"]:
            table.add_row(f["path"], str(f["loc"]))
        console.print(table)
    else:
        console.print("  [green]No at-risk files.[/green]")
    if report["top_people"]:
        console.print(
            "  Most concentrated people: "
            + ", ".join(
                f"{p['name']} ({p['files_over_40pct']} files >40%)" for p in report["top_people"]
            )
        )


@app.command()
def serve(
    port: int = typer.Option(None, "--port", help="API port (default from API_PORT or 8000)"),
) -> None:
    """Start the API (serves the built web UI when web/dist exists)."""
    import uvicorn

    from api.main import app as api_app

    settings = get_settings()
    web_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if (web_dist / "index.html").is_file():
        from api.main import mount_web

        mount_web(web_dist)
    uvicorn.run(api_app, host="127.0.0.1", port=port or settings.api_port)


@app.command()
def mcp(
    http: bool = typer.Option(False, "--http", help="Use streamable HTTP instead of stdio"),
    port: int | None = typer.Option(None, "--port"),
) -> None:
    """Start the MCP server (stdio by default)."""
    from mcp_server.server import run_server

    run_server(http=http, port=port)


@app.command()
def export(
    format: str = typer.Option("md", "--format", help="md or json"),
    repo: str | None = typer.Option(None, "--repo"),
) -> None:
    """Export the full knowledge base as Markdown or JSON."""
    from core.export.exporter import export_json, export_markdown

    repo_id = _resolve_repo(repo)
    with session_for(repo_id) as session:
        out = (
            export_json(session, repo_id) if format == "json" else export_markdown(session, repo_id)
        )
    print(out)


def app_entry() -> None:
    """Console-script entry point with friendly error reporting."""
    try:
        app()
    except HeirloomError as exc:
        console.print(f"[red]error ({exc.code})[/red]: {exc.message}")
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app_entry()
