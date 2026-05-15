"""SkillSentinel command-line interface.

Mirrors OpenClaw's verb-noun convention so the two tools feel native together.
Phase-0 implementation: ``scan`` works end-to-end against stub agents. All
other commands exit with code 2 ("not implemented") so users immediately know
what's wired and what isn't.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from skillsentinel.__about__ import version_string
from skillsentinel.orchestrator import Orchestrator
from skillsentinel.shared import ScanRequest

console = Console()


def _not_implemented(name: str) -> None:
    """Phase-0 placeholder: tell the user the command exists but isn't wired."""
    console.print(f"[yellow]`{name}` is not implemented yet (Phase-3 work).[/yellow]")
    sys.exit(2)


def _render_report(report) -> None:  # type: ignore[no-untyped-def]
    """Pretty-print a RiskReport to the terminal."""
    color = {
        "ALLOW": "green",
        "WARN": "yellow",
        "REVIEW": "magenta",
        "BLOCK": "red",
    }.get(report.verdict.value, "white")

    console.print(
        Panel.fit(
            f"[bold {color}]{report.verdict.value}[/bold {color}]    "
            f"risk {report.risk_score}/100    "
            f"confidence {report.confidence:.2f}",
            title=f"Bundle {report.bundle_sha[:12]}",
        )
    )

    if report.findings:
        table = Table("Severity", "Category", "Agent", "Message")
        for f in sorted(report.findings, key=lambda f: -f.confidence):
            table.add_row(f.severity.value, f.category.value, f.agent, f.message)
        console.print(table)
    else:
        console.print("[dim]No findings (Phase-0 stubs).[/dim]")

    console.print(f"\n[italic]{report.justification}[/italic]\n")


def _version_callback(value: bool) -> None:
    """Eager option callback so ``--version`` works without a subcommand."""
    if value:
        console.print(version_string())
        raise typer.Exit(0)


app = typer.Typer(
    name="skillsentinel",
    help="Multi-agent security scanner for AI agent skills.",
    no_args_is_help=False,
    add_completion=False,
)

gateway_app = typer.Typer(help="Gateway daemon control.", no_args_is_help=True)
config_app = typer.Typer(help="Configuration management.", no_args_is_help=True)
verdict_app = typer.Typer(help="Inspect cached verdicts.", no_args_is_help=True)
models_app = typer.Typer(help="LLM model selection.", no_args_is_help=True)

app.add_typer(gateway_app, name="gateway")
app.add_typer(config_app, name="config")
app.add_typer(verdict_app, name="verdict")
app.add_typer(models_app, name="models")


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Print version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Verbose output.",
    ),
) -> None:
    _ = (version, verbose)
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit(0)


@app.command()
def scan(
    bundle: Path = typer.Argument(..., exists=True, help="Path to a skill bundle."),
    policy: str = typer.Option("default", "--policy", "-p"),
    no_dynamic: bool = typer.Option(False, "--no-dynamic"),
    timeout: int = typer.Option(120, "--timeout", "-t", min=1, max=900),
) -> None:
    """Scan a skill bundle and emit a verdict."""
    request = ScanRequest(
        bundle_path=bundle,
        policy_name=policy,
        enable_dynamic=not no_dynamic,
        timeout_seconds=timeout,
    )
    orchestrator = Orchestrator()
    response = asyncio.run(orchestrator.scan(request))
    _render_report(response.report)


@app.command()
def doctor(
    repair: bool = typer.Option(False, "--repair"),
    deep: bool = typer.Option(False, "--deep"),
) -> None:
    """Diagnose the SkillSentinel installation."""
    _ = (repair, deep)
    _not_implemented("doctor")


@app.command()
def logs(
    follow: bool = typer.Option(False, "--follow", "-f"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Tail the gateway log."""
    _ = (follow, json_output)
    _not_implemented("logs")


@gateway_app.command("start")
def gateway_start() -> None:
    _not_implemented("gateway start")


@gateway_app.command("stop")
def gateway_stop() -> None:
    _not_implemented("gateway stop")


@gateway_app.command("restart")
def gateway_restart() -> None:
    _not_implemented("gateway restart")


@gateway_app.command("status")
def gateway_status() -> None:
    _not_implemented("gateway status")


@config_app.command("list")
def config_list() -> None:
    _not_implemented("config list")


@config_app.command("get")
def config_get(key: str = typer.Argument(...)) -> None:
    _ = key
    _not_implemented("config get")


@config_app.command("set")
def config_set(key: str = typer.Argument(...), value: str = typer.Argument(...)) -> None:
    _ = (key, value)
    _not_implemented("config set")


@verdict_app.command("show")
def verdict_show(bundle_sha: str = typer.Argument(...)) -> None:
    _ = bundle_sha
    _not_implemented("verdict show")


@verdict_app.command("export")
def verdict_export(bundle_sha: str = typer.Argument(...)) -> None:
    _ = bundle_sha
    _not_implemented("verdict export")


@models_app.command("set")
def models_set(model_id: str = typer.Argument(...)) -> None:
    _ = model_id
    _not_implemented("models set")


@models_app.command("list")
def models_list() -> None:
    _not_implemented("models list")


if __name__ == "__main__":
    app()
