from __future__ import annotations

from behave import given, when, then


@given("an evaluation run has completed")
def step_eval_completed(context) -> None:
    context.report = {
        "roots": [
            {
                "root_id": "llm-input-logging",
                "weakest_slot": {
                    "slot": "availability",
                    "p": 0.42,
                    "k": 0.58,
                    "evidence_ids": ["pytest:1", "semgrep:2"],
                },
            },
            {
                "root_id": "llm-privacy-redaction",
                "weakest_slot": {
                    "slot": "defeater_resistance",
                    "p": 0.36,
                    "k": 0.44,
                    "evidence_ids": ["redaction:3"],
                },
            },
        ],
    }
    context.next_actions = [
        {
            "collection": "pytest",
            "expected_impact": "Improve evidence coverage for weakest slot.",
        },
        {
            "collection": "semgrep",
            "expected_impact": "Increase static analysis support for weak slot.",
        },
    ]
    context.audit_events = [
        {
            "event": "voi_lite_scoring",
            "inputs": {"root": "llm-input-logging", "slot": "availability"},
        }
    ]


@when("I view the report")
def step_view_report(context) -> None:
    context.report_view = context.report


@then('each root should include "weakest_slot"')
def step_roots_have_weakest(context) -> None:
    roots = context.report_view.get("roots", [])
    assert roots, roots
    for root in roots:
        assert "weakest_slot" in root, root


@then("it should include the slot name, p, k, and evidence IDs used")
def step_weakest_fields(context) -> None:
    roots = context.report_view.get("roots", [])
    for root in roots:
        weakest = root.get("weakest_slot") or {}
        assert "slot" in weakest
        assert "p" in weakest
        assert "k" in weakest
        assert "evidence_ids" in weakest


@when('I request "next_actions"')
def step_request_next_actions(context) -> None:
    context.output = {"next_actions": context.next_actions}


@then("the output should list suggested evidence collections")
def step_actions_listed(context) -> None:
    actions = context.output.get("next_actions", [])
    assert actions, actions
    for action in actions:
        assert action.get("collection"), action


@then("each action should include an expected impact rationale")
def step_actions_expected_impact(context) -> None:
    actions = context.output.get("next_actions", [])
    for action in actions:
        assert action.get("expected_impact"), action


@then("the audit should record the VOI-lite scoring inputs")
def step_audit_voi(context) -> None:
    events = context.audit_events
    assert any(event.get("event") == "voi_lite_scoring" for event in events), events
