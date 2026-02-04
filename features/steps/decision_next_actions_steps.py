from __future__ import annotations

from behave import given, when, then

from praevisio.application.decision_service import build_decision
from praevisio.domain.entities import EvaluationResult
from praevisio.domain.evaluation_config import EvaluationConfig


@given('the overall verdict is "{verdict}"')
def step_overall_verdict(context, verdict: str) -> None:
    context.desired_overall = verdict


@when("the decision is produced")
def step_decision_produced(context) -> None:
    desired = getattr(context, "desired_overall", "block")
    if desired == "block":
        result = EvaluationResult(
            credence=0.6,
            verdict="red",
            details={
                "gates": {"credence>=threshold": False, "k_root>=tau": True},
                "evidence": {
                    "tests_skipped": True,
                    "semgrep_coverage": 0.4,
                    "violations_found": 0,
                },
                "evidence_refs": {},
                "k_root": 0.8,
                "applicable": True,
            },
        )
        evaluation = EvaluationConfig(
            promise_id="llm-input-logging",
            threshold=0.8,
            abductio_tau=0.7,
        )
    else:
        result = EvaluationResult(
            credence=0.9,
            verdict="green",
            details={
                "gates": {"credence>=threshold": True, "k_root>=tau": True},
                "evidence": {
                    "tests_skipped": False,
                    "semgrep_coverage": 1.0,
                    "violations_found": 0,
                },
                "evidence_refs": {},
                "k_root": 0.85,
                "applicable": True,
            },
        )
        evaluation = EvaluationConfig(
            promise_id="llm-input-logging",
            threshold=0.8,
            abductio_tau=0.7,
        )
    context.decision = build_decision(
        result,
        evaluation,
        enforcement_mode="ci-gate",
        fail_on_violation=True,
    )


@then('it should include "next_actions"')
def step_has_next_actions(context) -> None:
    assert "next_actions" in context.decision
    actions = context.decision["next_actions"]
    assert actions, actions


@then('each action should include "title", "rationale", and "expected_impact"')
def step_action_fields(context) -> None:
    actions = context.decision.get("next_actions") or []
    for action in actions:
        assert "title" in action
        assert "rationale" in action
        assert "expected_impact" in action


@then("each action should reference evidence IDs or missing evidence types")
def step_action_refs(context) -> None:
    actions = context.decision.get("next_actions") or []
    for action in actions:
        has_refs = bool(action.get("evidence_refs"))
        has_missing = bool(action.get("missing_evidence"))
        assert has_refs or has_missing, action
