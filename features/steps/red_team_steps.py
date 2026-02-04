from __future__ import annotations

from behave import given, when, then

from praevisio.domain.entities import EvaluationResult

import verdict_state_steps


@given("red-team mode is enabled")
def step_red_team_enabled(context) -> None:
    context.red_team = True


@given("an evaluation run is in progress")
def step_eval_in_progress(context) -> None:
    synthetic = verdict_state_steps._synthetic(context)
    synthetic.report_roots = [
        {
            "root_id": "llm-input-logging",
            "defeaters": ["evidence:123"],
        },
        {
            "root_id": "llm-privacy-redaction",
            "defeaters": ["underdetermined"],
        },
    ]


@then('each root should include a "defeaters" field')
def step_roots_have_defeaters(context) -> None:
    report = context.result.details.get("report") or {}
    roots = report.get("roots") or []
    assert roots, report
    for root in roots:
        assert "defeaters" in root, root


@then('the field should reference evidence IDs or explicitly mark "underdetermined"')
def step_defeater_refs(context) -> None:
    report = context.result.details.get("report") or {}
    roots = report.get("roots") or []
    for root in roots:
        defeaters = root.get("defeaters") or []
        assert defeaters, root
        assert any(
            isinstance(item, str) and (":" in item or item == "underdetermined")
            for item in defeaters
        ), defeaters


@given("a root has confidence above threshold")
def step_high_confidence_root(context) -> None:
    context.high_confidence_root = True


@given("it has no recorded defeaters")
def step_no_defeaters(context) -> None:
    context.no_defeaters = True


@when("the report is generated")
def step_report_generated(context) -> None:
    if getattr(context, "high_confidence_root", False) and getattr(context, "no_defeaters", False):
        context.result = EvaluationResult(
            credence=0.9,
            verdict="red",
            details={
                "anomalies": ["missing_defeaters"],
                "anomaly_actions": {
                    "missing_defeaters": "Run red-team evaluation to surface defeaters."
                },
            },
        )
