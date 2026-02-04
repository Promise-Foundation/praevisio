from __future__ import annotations

import json
import shlex
from pathlib import Path

from behave import given, when, then
from typer.testing import CliRunner

import praevisio.presentation.cli as cli_module
from praevisio.domain.entities import EvaluationResult


def _write_config(path: Path, promise_ids: list[str], severity: str) -> None:
    lines = [
        "evaluation:",
        f"  promise_id: {promise_ids[0]}",
        f"  severity: {severity}",
        "  threshold: 0.95",
        "  thresholds:",
        f"    {severity}: 0.95",
        "  pytest_targets: []",
        "  semgrep_rules_path: governance/evidence/semgrep_rules.yaml",
        "promises:",
    ]
    for pid in promise_ids:
        lines.append(f"  - {pid}")
    lines.append("hooks: []")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


@given(
    'a configuration listing promises "{first}" and "{second}" and "{third}"'
)
def step_config_promises(context, first: str, second: str, third: str) -> None:
    context.promise_ids = [first, second, third]
    context.severity = "high"
    context.config_path = Path(".praevisio.yaml")
    _write_config(context.config_path, context.promise_ids, context.severity)
    context.report_path = Path("logs/ci-gate-report.json")
    context.report_path.parent.mkdir(parents=True, exist_ok=True)
    context.runner = CliRunner()


@given('severity thresholds are configured for "{severity}"')
def step_severity_thresholds(context, severity: str) -> None:
    context.severity = severity
    if hasattr(context, "config_path") and hasattr(context, "promise_ids"):
        _write_config(context.config_path, context.promise_ids, context.severity)


@given('"{promise_id}" is critical and severity "{severity}"')
def step_promise_critical(context, promise_id: str, severity: str) -> None:
    context.critical_promises = set(getattr(context, "critical_promises", set()))
    context.critical_promises.add(promise_id)
    context.severity = severity


@given('"{promise_id}" verdict is "{verdict}"')
def step_promise_verdict(context, promise_id: str, verdict: str) -> None:
    verdicts = getattr(context, "verdicts", {})
    verdicts[promise_id] = verdict
    context.verdicts = verdicts


@given('all critical promises have verdict "{verdict}"')
def step_all_critical_verdict(context, verdict: str) -> None:
    verdicts = getattr(context, "verdicts", {})
    for pid in context.promise_ids:
        verdicts[pid] = verdict
    context.verdicts = verdicts


def _install_fake_service(context) -> None:
    verdicts = getattr(context, "verdicts", {})

    class FakeEvaluationService:
        def evaluate_path(self, path: str, *args, **kwargs) -> EvaluationResult:
            config = kwargs.get("config")
            promise_id = getattr(config, "promise_id", "unknown")
            verdict = verdicts.get(promise_id, "green")
            if verdict == "error":
                credence = 0.0
            elif verdict == "red":
                credence = 0.5
            else:
                credence = 0.99
            return EvaluationResult(
                credence=credence,
                verdict=verdict,
                details={"applicable": True},
            )

    context._original_build_service = getattr(cli_module, "build_evaluation_service", None)
    cli_module.build_evaluation_service = lambda: FakeEvaluationService()


def _restore_service(context) -> None:
    if getattr(context, "_original_build_service", None) is not None:
        cli_module.build_evaluation_service = context._original_build_service


@when('I run "praevisio ci-gate . --fail-on-violation --config .praevisio.yaml --output logs/ci-gate-report.json"')
def step_run_ci_gate_command(context) -> None:
    _install_fake_service(context)
    if context.report_path.exists():
        context.report_path.unlink()
    args = shlex.split(
        "ci-gate . --fail-on-violation --config .praevisio.yaml --output logs/ci-gate-report.json"
    )
    result = context.runner.invoke(cli_module.app, args)
    context.cli_result = result
    _restore_service(context)


@when("I run the CI gate with fail-on-violation enabled")
def step_run_ci_gate(context) -> None:
    _install_fake_service(context)
    if context.report_path.exists():
        context.report_path.unlink()
    args = [
        "ci-gate",
        ".",
        "--fail-on-violation",
        "--config",
        str(context.config_path),
        "--output",
        str(context.report_path),
    ]
    result = context.runner.invoke(cli_module.app, args)
    context.cli_result = result
    _restore_service(context)


@then(
    '"logs/ci-gate-report.json" should contain a list of results for all configured promises'
)
def step_report_contains_all(context) -> None:
    assert context.report_path.exists(), "Missing report file"
    report = json.loads(context.report_path.read_text(encoding="utf-8"))
    results = report.get("results") if isinstance(report, dict) else report
    assert isinstance(results, list), report
    ids = {item.get("id") for item in results}
    assert set(context.promise_ids) == ids, ids


@then('it should include "policy_id" or a hash of the policy rules used')
def step_report_policy(context) -> None:
    report = json.loads(context.report_path.read_text(encoding="utf-8"))
    assert "policy_id" in report or "policy_hash" in report, report


@then("the CI gate should exit non-zero")
def step_ci_gate_exit_nonzero(context) -> None:
    assert context.cli_result.exit_code != 0, context.cli_result.output

