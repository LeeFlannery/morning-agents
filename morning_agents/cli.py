from __future__ import annotations

import asyncio
import sys

import typer
from rich.console import Console
from rich.text import Text

from morning_agents.agents.brewmaster import BrewmasterAgent
from morning_agents.agents.cross_ref import CrossRefAgent
from morning_agents.agents.devenv import DevEnvAgent
from morning_agents.agents.pr_queue import PRQueueAgent
from morning_agents.contracts.models import AgentResult, AgentStatus, BriefingOutput, Severity
from morning_agents.orchestrator import Orchestrator
from morning_agents.persistence import RUNS_DIR, get_latest_run, list_runs, load_briefing

app = typer.Typer(add_completion=False, invoke_without_command=True)
console = Console(stderr=True)  # Rich output → stderr (human-readable, doesn't pollute pipes)

_AGENTS = {
    "brewmaster": BrewmasterAgent,
    "devenv": DevEnvAgent,
    "pr_queue": PRQueueAgent,
    "cross_ref": CrossRefAgent,
}

_SEVERITY_STYLE: dict[Severity, tuple[str, str]] = {
    Severity.info:         ("green",    "INFO  "),
    Severity.warning:      ("yellow",   "WARN  "),
    Severity.action_needed:("bold red", "ACTION"),
}

_XREF_ICON = {
    Severity.info:          "ℹ️ ",
    Severity.warning:       "⚠️ ",
    Severity.action_needed: "🔴",
}


def _render(briefing: BriefingOutput) -> None:
    quiet = briefing.config.quiet_mode
    ts = briefing.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    agents_n = briefing.summary.agents_run
    dur = f"{briefing.duration_ms / 1000:.1f}s"
    console.rule(f"[bold]Morning Briefing[/bold]  {ts}  ·  {agents_n} agent{'s' if agents_n != 1 else ''}  ·  {dur}")
    console.print()

    for result in briefing.agent_results:
        _render_agent(result, quiet=quiet)

    if briefing.cross_references:
        console.print("  [bold]🔗 Cross-References[/bold]")
        for xref in briefing.cross_references:
            icon = _XREF_ICON.get(xref.severity, "❓")
            console.print(f"   {icon} {xref.title}")
            if xref.detail and not briefing.config.quiet_mode:
                console.print(f"          [dim]{xref.detail}[/dim]")
        console.print()

    s = briefing.summary
    parts = [f"[bold]{s.total_findings}[/bold] findings"]
    for sev, count in sorted(s.by_severity.items()):
        style, _ = _SEVERITY_STYLE.get(Severity(sev), ("white", sev.upper()))
        parts.append(f"[{style}]{count} {sev}[/{style}]")
    console.print("  " + "  ·  ".join(parts))
    console.print()


def _render_agent(result: AgentResult, *, quiet: bool = False) -> None:
    if result.status == AgentStatus.error:
        console.print(f"  [bold red]{result.agent_display_name}[/bold red]  [red]ERROR: {result.error}[/red]")
        console.print()
        return

    console.print(f"  [bold]{result.agent_display_name}[/bold]")

    for finding in result.findings:
        style, label = _SEVERITY_STYLE.get(finding.severity, ("white", "?????"))
        badge = Text(f" {label}", style=f"bold {style}")
        title = Text(f"  {finding.title}")
        line = Text.assemble(badge, title)
        console.print("   ", line)
        if finding.detail and not quiet:
            console.print(f"          [dim]{finding.detail}[/dim]")

    console.print()


@app.callback()
def main(
    ctx: typer.Context,
    agent: list[str] = typer.Option(
        ["brewmaster", "devenv", "pr_queue", "cross_ref"],
        "--agent", "-a",
        help="Agents to run (repeat for multiple).",
    ),
    parallel: bool = typer.Option(True, help="Run agents in parallel."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress detail lines in progress output."),
    json_output: bool = typer.Option(False, "--json", help="Output JSON to stdout, no Rich rendering."),
    no_persist: bool = typer.Option(False, "--no-persist", help="Skip saving to runs/."),
) -> None:
    """Run the morning briefing. Progress → stderr. JSON results → stdout."""
    if ctx.invoked_subcommand is not None:
        return

    unknown = set(agent) - set(_AGENTS)
    if unknown:
        typer.echo(f"Unknown agent(s): {', '.join(sorted(unknown))}", err=True)
        raise typer.Exit(1)

    agent_classes = [_AGENTS[name] for name in agent]
    orchestrator = Orchestrator(agent_classes=agent_classes, quiet_mode=quiet, parallel=parallel, persist=not no_persist)
    briefing = asyncio.run(orchestrator.run())

    if json_output:
        print(briefing.model_dump_json(indent=2))
    else:
        _render(briefing)
        print(briefing.model_dump_json(indent=2))  # stdout — always, pipeable

    if any(r.status == AgentStatus.error for r in briefing.agent_results):
        raise typer.Exit(1)


@app.command()
def history(limit: int = typer.Option(10, help="Number of runs to show.")):
    """Show recent briefing run history."""
    files = list_runs(limit=limit)
    if not files:
        console.print("No runs found. Run [bold]morning-agents[/bold] first.")
        return
    console.print("\nRecent runs:")
    for f in files:
        b = load_briefing(f)
        ts = b.generated_at.strftime("%Y-%m-%d %H:%M")
        n = b.summary.agents_run
        parts = [f"  {ts}  {n} agent{'s' if n != 1 else ''}"]
        for sev, count in sorted(b.summary.by_severity.items()):
            style, label = _SEVERITY_STYLE.get(Severity(sev), ("white", sev))
            parts.append(f"[{style}]{count} {sev}[/{style}]")
        console.print("  " + "  ·  ".join(parts))
    console.print()


@app.command()
def last():
    """Show the most recent briefing run."""
    b = get_latest_run()
    if b is None:
        console.print("No runs found. Run [bold]morning-agents[/bold] first.")
        return
    _render(b)


@app.command()
def show(run_id: str):
    """Show a specific briefing run by ID."""
    try:
        _render(load_briefing(RUNS_DIR / f"{run_id}.json"))
    except FileNotFoundError:
        console.print(f"[red]Run not found:[/red] {run_id}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
