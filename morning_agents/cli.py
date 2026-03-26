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


@app.command(name="eval")
def eval_cmd():
    """Run all golden test cases against frozen fixtures (requires ANTHROPIC_API_KEY)."""
    asyncio.run(_run_eval())


async def _run_eval() -> None:
    import json
    import yaml
    from pathlib import Path
    from evals.mocks import MockMCPSession, load_upstream_fixture
    from evals.judge import judge_agent_output
    from morning_agents.orchestrator.resources import ResourceContext

    GOLDEN = Path("evals/golden")
    ctx = ResourceContext(
        semaphore=asyncio.Semaphore(4),
        workspace_root=Path("/tmp/morning-agents-eval"),
        briefing_id="eval",
    )

    console.print("\n[bold]Golden Test Suite[/bold]\n")

    async def _run_suite(display: str, agent_name: str, sessions: dict, upstream_arg, criteria_path: Path, frozen_input: dict) -> tuple[int, int]:
        criteria = yaml.safe_load(criteria_path.read_text())
        agent = _AGENTS[agent_name](resources=ctx)
        result = await agent.run(sessions=sessions, upstream=upstream_arg)
        result.compute_summary()
        verdict = await judge_agent_output(
            agent_name=agent_name,
            findings=[f.model_dump() for f in result.findings],
            criteria=criteria,
            frozen_input=frozen_input,
        )
        score_pct = f"{verdict.score:.0%}"
        icon = "✅" if verdict.score >= 0.8 else "⚠️"
        console.print(f"  [bold]{display}[/bold] ({verdict.total_checks} checks)")
        for r in verdict.results:
            status = "[green]✅[/green]" if r.passed else "[red]❌[/red]"
            console.print(f"    {status} {r.check_id}: {r.reasoning[:100]}")
        console.print(f"    Score: {score_pct} ({verdict.passed}/{verdict.total_checks}) {icon}\n")
        return verdict.total_checks, verdict.passed

    # Depth-0 suites (no inter-agent dependencies) run in parallel
    outdated = json.loads((GOLDEN / "brewmaster/outdated_packages.json").read_text())
    doctor = json.loads((GOLDEN / "brewmaster/doctor_warnings.json").read_text())
    brew_data = {"list_outdated": outdated["output"], "get_doctor_status": doctor["output"]}

    devenv_data = json.loads((GOLDEN / "devenv/tool_versions.json").read_text())

    pr_raw = json.loads((GOLDEN / "pr_queue/search_results.json").read_text())
    pr_data = {"search_pull_requests": pr_raw["output"]}

    depth0_results = await asyncio.gather(
        _run_suite("🍺 Brewmaster", "brewmaster", {"homebrew-mcp": MockMCPSession(brew_data)}, None, GOLDEN / "brewmaster/criteria.yaml", brew_data),
        _run_suite("🛠️  DevEnv", "devenv", {"devenv-mcp": MockMCPSession(devenv_data)}, None, GOLDEN / "devenv/criteria.yaml", devenv_data),
        _run_suite("🔀 PR Queue", "pr_queue", {"github-mcp": MockMCPSession(pr_data)}, None, GOLDEN / "pr_queue/criteria.yaml", pr_data),
    )

    # CrossRef depends on upstream results — runs after depth-0
    upstream = load_upstream_fixture(str(GOLDEN / "cross_ref/upstream_results.json"))
    frozen_upstream = {name: r.model_dump() for name, r in upstream.items()}
    crossref_result = await _run_suite("🔗 Cross-Reference", "cross_ref", {}, upstream, GOLDEN / "cross_ref/criteria.yaml", frozen_upstream)

    all_results = [*depth0_results, crossref_result]
    total_checks = sum(c for c, _ in all_results)
    total_passed = sum(p for _, p in all_results)
    overall_pct = f"{total_passed / total_checks:.0%}" if total_checks else "0%"
    icon = "✅" if total_checks and total_passed / total_checks >= 0.8 else "⚠️"
    console.print(f"  [bold]Overall: {overall_pct} ({total_passed}/{total_checks}) {icon}[/bold]\n")


@app.command(name="diff")
def diff_runs(
    run_a: str = typer.Argument(..., help="Baseline run ID (e.g. brief-2026-03-15-071418)"),
    run_b: str = typer.Option(None, help="Current run ID. Defaults to most recent run."),
):
    """Compare two briefing runs for regressions."""
    from evals.regression import detect_regressions

    baseline = load_briefing(RUNS_DIR / f"{run_a}.json")

    if run_b:
        current = load_briefing(RUNS_DIR / f"{run_b}.json")
        current_id = run_b
    else:
        current = get_latest_run()
        if current is None:
            console.print("[red]No runs found.[/red]")
            raise typer.Exit(1)
        current_id = current.briefing_id

    console.print("\n[bold]Regression Report[/bold]")
    console.print(f"  Baseline: {run_a}")
    console.print(f"  Current:  {current_id}\n")

    flags = detect_regressions(baseline, current)
    flag_map: dict[str, list] = {}
    for f in flags:
        flag_map.setdefault(f.agent_name, []).append(f)

    all_agents = {r.agent_name for r in baseline.agent_results} | {r.agent_name for r in current.agent_results}
    all_agents.add("_orchestrator")

    for agent_name in sorted(all_agents):
        agent_flags = flag_map.get(agent_name, [])
        if not agent_flags:
            if agent_name != "_orchestrator":
                console.print(f"  [green]✅[/green] {agent_name}: no regressions")
        else:
            for flag in agent_flags:
                icon = "[bold red]🔴[/bold red]" if flag.severity == "critical" else "[yellow]⚠️[/yellow]"
                console.print(f"  {icon} {agent_name}: {flag.description}")

    dag_flags = flag_map.get("_orchestrator", [])
    if dag_flags:
        for f in dag_flags:
            console.print(f"  [yellow]⚠️[/yellow]  DAG stages: {f.description}")
    else:
        console.print(f"  [green]✅[/green] DAG stages: unchanged")

    critical = sum(1 for f in flags if f.severity == "critical")
    warnings = sum(1 for f in flags if f.severity == "warning")
    console.print(f"\n  {len(flags)} flag{'s' if len(flags) != 1 else ''} ({critical} critical, {warnings} warning)\n")

    if critical > 0:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
