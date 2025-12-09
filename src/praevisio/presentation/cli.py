from __future__ import annotations

"""Typer-based command-line interface for praevisio.

Commands map to application services. Run `python -m praevisio --help` to see
available commands.
"""

import json
import sys
import stat
from pathlib import Path
import typer

from ..application.configuration_service import ConfigurationService
from ..application.installation_service import InstallationService
from ..application.services import HookOrchestrationService, evaluate_commit
from ..application.validation_service import ValidationService
from ..domain.value_objects import HookType
from ..infrastructure.config import YamlConfigLoader
from ..infrastructure.filesystem import LocalFileSystemService
from ..infrastructure.git import InMemoryGitRepository
from ..infrastructure.process import RecordingProcessExecutor


app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.command()
def install(config_path: str = ".praevisio.yaml") -> None:
    fs = LocalFileSystemService()
    installer = InstallationService(fs, config_path)
    path = installer.install()
    typer.echo(f"Installed default config at {path}")


@app.command("pre-commit")
def pre_commit(
    path: str = typer.Argument(".", help="Path to the repository/commit to evaluate."),
    threshold: float = typer.Option(
        0.95, "--threshold", help="Credence threshold required to pass the pre-commit gate."
    ),
) -> None:
    """Local governance gate to block commits when credence is below threshold."""
    result = evaluate_commit(path)
    if result.credence < threshold:
        typer.echo("[praevisio][pre-commit] ❌ Critical promises not satisfied. Commit aborted.")
        raise typer.Exit(code=1)
    typer.echo("[praevisio][pre-commit] ✅ All critical promises satisfied.")


@app.command("evaluate-commit")
def evaluate_commit_cmd(
    path: str,
    json_output: bool = typer.Option(
        False,
        "--json-output",
        "--json",
        help="Print structured JSON output instead of plain text.",
    ),
) -> None:
    """Evaluate a single commit directory and print credence and verdict."""
    result = evaluate_commit(path)
    if json_output:
        typer.echo(json.dumps({
            "credence": result.credence,
            "verdict": result.verdict,
            "details": result.details,
        }, indent=2))
    else:
        typer.echo(f"Credence: {result.credence:.3f}")
        typer.echo(f"Verdict: {result.verdict}")


@app.command("ci-gate")
def ci_gate(
    path: str = typer.Argument(".", help="Path to the target repository/commit."),
    severity: str = typer.Option("high", "--severity", help="Severity level to enforce."),
    fail_on_violation: bool = typer.Option(
        False, "--fail-on-violation", help="Exit with error on violations."
    ),
    output: str = typer.Option(
        "logs/ci-gate-report.json",
        "--output",
        help="Where to write JSON report of evaluated promises.",
    ),
    threshold: float = typer.Option(
        0.95, "--threshold", help="Credence threshold for passing high-severity promises."
    ),
) -> None:
    """Run Praevisio as a CI governance gate."""
    result = evaluate_commit(path)

    report_entry = {
        "id": "llm-input-logging",
        "credence": result.credence,
        "verdict": result.verdict,
        "threshold": threshold,
        "severity": severity,
    }
    report = [report_entry]

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    should_fail = fail_on_violation and any(r["credence"] < r["threshold"] for r in report)
    if should_fail:
        typer.echo("[praevisio][ci-gate] ❌ GATE FAILED")
        sys.exit(1)

    typer.echo("[praevisio][ci-gate] ✅ GATE PASSED")


@app.command("install-hooks")
def install_hooks(
    git_dir: str = typer.Option(
        ".", "--git-dir", help="Root of the git repository where hooks should be installed."
    )
) -> None:
    """Install a git pre-commit hook that runs `praevisio pre-commit`."""
    repo_root = Path(git_dir).resolve()
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "pre-commit"
    script = """#!/usr/bin/env sh
# Praevisio governance pre-commit hook

praevisio pre-commit
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
  echo "[praevisio][pre-commit] ❌ Critical promises not satisfied. Commit aborted."
  exit "$STATUS"
fi
exit 0
"""
    hook_path.write_text(script, encoding="utf-8")
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    typer.echo(f"Installed pre-commit hook at {hook_path}")


def main() -> None:
    app()
