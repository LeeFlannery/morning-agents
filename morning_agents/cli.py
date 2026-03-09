from __future__ import annotations

import asyncio

import typer
from rich.console import Console
from rich.text import Text

from morning_agents.agents.brewmaster import BrewmasterAgent
from morning_agents.contracts.models import AgentResult, AgentStatus, BriefingOutput, Severity
from morning_agents.orchestrator import Orchestrator

app = typer.Typer(add_completion=False)
console = Console()

_AGENTS = {"brewmaster": BrewmasterAgent}

_SEVERITY_STYLE: dict[Severity, tuple[str, str]] = {
    Severity.info:         ("green",    "INFO  "),
    Severity.warning:      ("yellow",   "WARN  "),
    Severity.action_needed:("bold red", "ACTION"),
}


def _render(briefing: BriefingOutput) -> None:
    ts = briefing.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    agents_n = briefing.summary.agents_run
    dur = f"{briefing.duration_ms / 1000:.1f}s"
    console.rule(f"[bold]Morning Briefing[/bold]  {ts}  ·  {agents_n} agent{'s' if agents_n != 1 else ''}  ·  {dur}")
    console.print()

    for result in briefing.agent_results:
        _render_agent(result)

    s = briefing.summary
    parts = [f"[bold]{s.total_findings}[/bold] findings"]
    for sev, count in sorted(s.by_severity.items()):
        style, _ = _SEVERITY_STYLE.get(Severity(sev), ("white", sev.upper()))
        parts.append(f"[{style}]{count} {sev}[/{style}]")
    console.print("  " + "  ·  ".join(parts))
    console.print()


def _render_agent(result: AgentResult) -> None:
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
        if finding.detail:
            console.print(f"          [dim]{finding.detail}[/dim]")

    console.print()


@app.command()
def main(
    agent: list[str] = typer.Option(
        ["brewmaster"],
        "--agent", "-a",
        help="Agents to run (repeat for multiple).",
    ),
    parallel: bool = typer.Option(True, help="Run agents in parallel."),
    json_output: bool = typer.Option(False, "--json", help="Print raw JSON output."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress detail lines."),
) -> None:
    """Run the morning briefing."""
    unknown = set(agent) - set(_AGENTS)
    if unknown:
        typer.echo(f"Unknown agent(s): {', '.join(sorted(unknown))}", err=True)
        raise typer.Exit(1)

    agents = [_AGENTS[name]() for name in agent]
    orchestrator = Orchestrator(agents=agents, quiet_mode=quiet, parallel=parallel)
    briefing = asyncio.run(orchestrator.run())

    if json_output:
        print(briefing.model_dump_json(indent=2))
    else:
        _render(briefing)

    if any(r.status == AgentStatus.error for r in briefing.agent_results):
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
