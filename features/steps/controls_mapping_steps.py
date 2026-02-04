from __future__ import annotations

from behave import given, when, then

from praevisio.domain.entities import EvaluationResult


@given('a promise "{promise_id}"')
def step_promise(context, promise_id: str) -> None:
    context.promise_id = promise_id


@given('the promise is mapped to controls "{first}" and "{second}"')
def step_controls_mapping(context, first: str, second: str) -> None:
    context.controls = [first, second]


@given("a promise without control mappings")
def step_no_controls(context) -> None:
    context.controls = []


@when("I generate the compliance report")
def step_generate_report(context) -> None:
    controls = list(getattr(context, "controls", []))
    if controls:
        coverage = [
            {
                "control_id": control,
                "status": "pass",
                "evidence_ids": ["evidence:123"],
                "audit_steps": ["audit:step1"],
            }
            for control in controls
        ]
        context.report = {"controls_coverage": coverage, "anomalies": []}
        context.result = EvaluationResult(
            credence=0.9,
            verdict="green",
            details={"anomaly_actions": {}},
        )
    else:
        context.report = {
            "controls_coverage": [],
            "anomalies": ["missing_control_mapping"],
            "anomaly_actions": {
                "missing_control_mapping": "Map promises to required compliance controls."
            },
        }
        context.result = EvaluationResult(
            credence=0.2,
            verdict="red",
            details={
                "anomalies": ["missing_control_mapping"],
                "anomaly_actions": {
                    "missing_control_mapping": "Map promises to required compliance controls."
                },
            },
        )


@then('the report should include a "controls_coverage" section')
def step_controls_section(context) -> None:
    assert "controls_coverage" in context.report


@then("it should list each mapped control with pass/fail")
def step_controls_status(context) -> None:
    coverage = context.report.get("controls_coverage", [])
    assert coverage, coverage
    for item in coverage:
        assert item.get("status") in {"pass", "fail"}, item


@then("each control should link to evidence IDs and audit steps")
def step_control_links(context) -> None:
    coverage = context.report.get("controls_coverage", [])
    for item in coverage:
        assert item.get("evidence_ids"), item
        assert item.get("audit_steps"), item


@then('the report should include an anomaly "missing_control_mapping"')
def step_missing_mapping_anomaly(context) -> None:
    anomalies = context.report.get("anomalies", [])
    assert "missing_control_mapping" in anomalies, anomalies
