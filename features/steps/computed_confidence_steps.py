from __future__ import annotations

from behave import given, when, then

from praevisio.application.decision_service import add_notification, build_decision
from praevisio.domain.entities import EvaluationResult
from praevisio.domain.evaluation_config import EvaluationConfig


def _ensure_context_defaults(context) -> None:
    if not hasattr(context, "severity"):
        context.severity = "high"
    if not hasattr(context, "credence"):
        context.credence = 0.6
    if not hasattr(context, "verdict"):
        context.verdict = "red"
    if not hasattr(context, "k_root"):
        context.k_root = 0.6


@given('a violated promise with severity "{severity}"')
def step_violated_with_severity(context, severity: str) -> None:
    context.severity = severity
    context.verdict = "red"


@given("a violated promise with credence {credence:f}")
def step_violated_with_credence(context, credence: float) -> None:
    context.credence = credence
    context.verdict = "red"
    context.k_root = 0.9 if credence >= 0.9 else 0.4


@given('a promise verdict is "{verdict}"')
def step_verdict_is(context, verdict: str) -> None:
    context.verdict = verdict
    if verdict == "error":
        context.k_root = 0.2
        context.credence = 0.0


@when("a decision is produced")
def step_decision_produced(context) -> None:
    _ensure_context_defaults(context)
    details = {
        "k_root": context.k_root,
        "applicable": True,
        "evidence": {"violations_found": 1},
    }
    if context.verdict == "error":
        details["semgrep_error"] = "semgrep error"
    result = EvaluationResult(
        credence=context.credence,
        verdict=context.verdict,
        details=details,
    )
    evaluation = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.8,
        severity=context.severity,
    )
    context.decision = build_decision(
        result,
        evaluation,
        enforcement_mode="ci-gate",
        fail_on_violation=True,
    )
    context.decision = add_notification(
        context.decision,
        evaluation=evaluation,
        result=result,
    )


@then('notification.impact should be "{expected}"')
def step_notification_impact(context, expected: str) -> None:
    impact = context.decision["notification"].get("impact")
    assert impact == expected, impact


@then('notification.likelihood should be "{expected:w}"')
def step_notification_likelihood(context, expected: str) -> None:
    likelihood = context.decision["notification"].get("likelihood")
    assert likelihood == expected, likelihood


@then('notification.confidence should be "{expected:w}"')
def step_notification_confidence(context, expected: str) -> None:
    confidence = context.decision["notification"].get("confidence")
    assert confidence == expected, confidence


@then('notification.likelihood should be "{first}" or "{second}"')
def step_notification_likelihood_band(context, first: str, second: str) -> None:
    likelihood = context.decision["notification"].get("likelihood")
    assert likelihood in {first, second}, likelihood


@then('notification.confidence should be "{first}" or "{second}"')
def step_notification_confidence_band(context, first: str, second: str) -> None:
    confidence = context.decision["notification"].get("confidence")
    assert confidence in {first, second}, confidence
