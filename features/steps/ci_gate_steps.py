from __future__ import annotations

import json
from pathlib import Path

from behave import given, when, then
from typer.testing import CliRunner

import praevisio.presentation.cli as cli_module
from praevisio.domain.entities import EvaluationResult


@given('a high-severity logging promise "{promise_id}" with threshold 0.95')
def step_high_severity_promise(context, promise_id: str) -> None:
    """
    Record the high-severity promise context for the CI gate.
    """
    context.promise_id = promise_id
    context.threshold = 0.95
    context.severity = "high"
    context.runner = CliRunner()
    context.report_path = Path("logs/ci-gate-report.json")


@given("the evaluation credence will be {credence:f}")
def step_mock_evaluate_commit(context, credence: float) -> None:
    """
    Stub evaluate_commit so we can simulate credence without external tools.
    """
    context.credence = credence
    verdict = "green" if credence >= context.threshold else "red"

    def fake_evaluate_commit(path: str) -> EvaluationResult:
        return EvaluationResult(
            credence=credence,
            verdict=verdict,
            details={
                "test_passes": credence >= context.threshold,
                "semgrep_coverage": 1.0,
            },
        )

    context._original_evaluate_commit = getattr(cli_module, "evaluate_commit", None)
    cli_module.evaluate_commit = fake_evaluate_commit


@when('I run the CI gate for severity "high" with fail-on-violation enabled')
def step_run_ci_gate(context) -> None:
    """
    Invoke the Typer CLI app as 'praevisio ci-gate ...' using CliRunner.
    """
    if context.report_path.exists():
        context.report_path.unlink()

    args = [
        "ci-gate",
        "--severity",
        context.severity,
        "--fail-on-violation",
        "--output",
        str(context.report_path),
    ]

    result = context.runner.invoke(cli_module.app, args)
    context.cli_result = result

    if getattr(context, "_original_evaluate_commit", None) is not None:
        cli_module.evaluate_commit = context._original_evaluate_commit


@then("the CI gate should pass")
def step_ci_gate_pass(context) -> None:
    assert (
        context.cli_result.exit_code == 0
    ), f"Expected exit code 0, got {context.cli_result.exit_code}.\nOutput:\n{context.cli_result.output}"


@then("the CI gate should fail")
def step_ci_gate_fail(context) -> None:
    assert (
        context.cli_result.exit_code != 0
    ), f"Expected non-zero exit code, got {context.cli_result.exit_code}.\nOutput:\n{context.cli_result.output}"


@then('the report should contain a "{expected_verdict}" verdict for promise "{promise_id}"')
def step_report_contains_verdict(context, expected_verdict: str, promise_id: str) -> None:
    assert context.report_path.exists(), f"Report file not found at {context.report_path}"

    with context.report_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    items = data if isinstance(data, list) else [data]
    matching = [item for item in items if item.get("id") == promise_id]
    assert matching, f"No report entry found for promise id={promise_id}. Got: {items}"

    entry = matching[0]
    actual_verdict = entry.get("verdict")
    assert (
        actual_verdict == expected_verdict
    ), f"Expected verdict {expected_verdict}, got {actual_verdict}. Full entry: {entry}"
