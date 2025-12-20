from __future__ import annotations

"""Typer-based command-line interface for praevisio.

Commands map to application services. Run `python -m praevisio --help` to see
available commands.
"""

import json
import stat
from pathlib import Path
from typing import Optional
import typer

from ..application.evaluation_service import EvaluationService
from ..application.installation_service import InstallationService
from ..domain.evaluation_config import EvaluationConfig
from ..infrastructure.config import YamlConfigLoader
from ..infrastructure.filesystem import LocalFileSystemService


app = typer.Typer(add_completion=False, no_args_is_help=True)


def build_evaluation_service() -> EvaluationService:
    return EvaluationService()


def load_configuration(path: str):
    loader = YamlConfigLoader()
    try:
        return loader.load(path)
    except FileNotFoundError:
        typer.echo(f"[praevisio] Config not found: {path}")
        raise typer.Exit(code=2)


@app.command()
def install(config_path: str = ".praevisio.yaml") -> None:
    fs = LocalFileSystemService()
    installer = InstallationService(fs, config_path)
    path = installer.install()
    typer.echo(f"Installed default config at {path}")


@app.command("pre-commit")
def pre_commit(
    path: str = typer.Argument(".", help="Path to the repository/commit to evaluate."),
    threshold: Optional[float] = typer.Option(
        None, "--threshold", help="Credence threshold required to pass the pre-commit gate."
    ),
    config_path: str = typer.Option(
        ".praevisio.yaml", "--config", help="Path to Praevisio configuration file."
    ),
) -> None:
    """Local governance gate to block commits when credence is below threshold."""
    service = build_evaluation_service()
    config = load_configuration(config_path)
    evaluation = config.evaluation
    effective_threshold = threshold if threshold is not None else evaluation.threshold
    evaluation = EvaluationConfig(
        promise_id=evaluation.promise_id,
        threshold=effective_threshold,
        pytest_args=evaluation.pytest_args,
        pytest_targets=evaluation.pytest_targets,
        semgrep_rules_path=evaluation.semgrep_rules_path,
        thresholds=evaluation.thresholds,
    )
    result = service.evaluate_path(path, config=evaluation)
    applicable = result.details.get("applicable", True)
    if applicable and (result.credence or 0.0) < evaluation.threshold:
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
    threshold: Optional[float] = typer.Option(
        None, "--threshold", help="Credence threshold required to pass the evaluation."
    ),
    config_path: str = typer.Option(
        ".praevisio.yaml", "--config", help="Path to Praevisio configuration file."
    ),
) -> None:
    """Evaluate a single commit directory and print credence and verdict."""
    service = build_evaluation_service()
    config = load_configuration(config_path)
    evaluation = config.evaluation
    effective_threshold = threshold if threshold is not None else evaluation.threshold
    evaluation = EvaluationConfig(
        promise_id=evaluation.promise_id,
        threshold=effective_threshold,
        pytest_args=evaluation.pytest_args,
        pytest_targets=evaluation.pytest_targets,
        semgrep_rules_path=evaluation.semgrep_rules_path,
        thresholds=evaluation.thresholds,
    )
    result = service.evaluate_path(path, config=evaluation)
    if json_output:
        typer.echo(json.dumps({
            "credence": result.credence,
            "verdict": result.verdict,
            "details": result.details,
        }, indent=2))
    else:
        credence_display = "n/a" if result.credence is None else f"{result.credence:.3f}"
        typer.echo(f"Credence: {credence_display}")
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
    threshold: Optional[float] = typer.Option(
        None, "--threshold", help="Credence threshold for passing high-severity promises."
    ),
    config_path: str = typer.Option(
        ".praevisio.yaml", "--config", help="Path to Praevisio configuration file."
    ),
) -> None:
    """Run Praevisio as a CI governance gate."""
    service = build_evaluation_service()
    config = load_configuration(config_path)
    evaluation = config.evaluation
    severity_threshold = evaluation.thresholds.get(severity)
    if threshold is not None:
        effective_threshold = threshold
    elif severity_threshold is not None:
        effective_threshold = severity_threshold
    else:
        effective_threshold = evaluation.threshold
    evaluation = EvaluationConfig(
        promise_id=evaluation.promise_id,
        threshold=effective_threshold,
        pytest_args=evaluation.pytest_args,
        pytest_targets=evaluation.pytest_targets,
        semgrep_rules_path=evaluation.semgrep_rules_path,
        thresholds=evaluation.thresholds,
    )
    result = service.evaluate_path(path, config=evaluation)

    report_entry = {
        "id": evaluation.promise_id,
        "credence": result.credence,
        "verdict": result.verdict,
        "threshold": evaluation.threshold,
        "severity": severity,
        "applicable": result.details.get("applicable", True),
    }
    report = [report_entry]

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    should_fail = False
    if fail_on_violation:
        for entry in report:
            applicable = entry.get("applicable", True)
            credence = entry.get("credence")
            if applicable and credence is not None and credence < entry["threshold"]:
                should_fail = True
                break
    if should_fail:
        typer.echo("[praevisio][ci-gate] ❌ GATE FAILED")
        raise typer.Exit(code=1)

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
