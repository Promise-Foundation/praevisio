from __future__ import annotations

from behave import given, when, then


@given('an evidence bundle with "observations", "appendices", and "conclusions"')
def step_evidence_bundle(context) -> None:
    context.evidence_bundle = {
        "observations": ["obs-1", "obs-2"],
        "appendices": ["app-1"],
        "conclusions": ["con-1"],
    }


@given("staged disclosure is enabled")
def step_staged_enabled(context) -> None:
    context.staged_disclosure = True
    context.audit_events = []


@when("I run evaluation in Phase A")
def step_run_phase_a(context) -> None:
    context.evaluator_input = {
        "observations": context.evidence_bundle.get("observations", [])
    }
    context.audit_events.append(
        {"event": "evidence_stage", "stage": "observations_only"}
    )


@then('the evaluator input should include only "observations"')
def step_only_observations(context) -> None:
    assert "observations" in context.evaluator_input
    assert "appendices" not in context.evaluator_input
    assert "conclusions" not in context.evaluator_input


@then('the audit should record "evidence_stage" as "observations_only"')
def step_audit_stage_a(context) -> None:
    assert any(
        e.get("event") == "evidence_stage" and e.get("stage") == "observations_only"
        for e in context.audit_events
    ), context.audit_events


@given("Phase A is not locked")
def step_phase_a_not_locked(context) -> None:
    context.phase_a_locked = False


@when('a component requests "conclusions"')
def step_request_conclusions(context) -> None:
    if not getattr(context, "phase_a_locked", False):
        context.access_denied = True
        context.audit_events.append(
            {"event": "evidence_access_violation", "resource": "conclusions"}
        )


@then("the request should be denied")
def step_request_denied(context) -> None:
    assert context.access_denied is True


@then('the audit should include an "evidence_access_violation" anomaly')
def step_audit_violation(context) -> None:
    assert any(
        e.get("event") == "evidence_access_violation" for e in context.audit_events
    ), context.audit_events


@given("Phase A is locked")
def step_phase_a_locked(context) -> None:
    context.phase_a_locked = True


@when("I run Phase B oracle comparison")
def step_run_phase_b(context) -> None:
    context.evaluator_input = {
        "observations": context.evidence_bundle.get("observations", []),
        "conclusions": context.evidence_bundle.get("conclusions", []),
    }
    context.audit_events.append(
        {"event": "evidence_stage", "stage": "oracle_comparison"}
    )


@then("conclusions may be used")
def step_conclusions_used(context) -> None:
    assert "conclusions" in context.evaluator_input


@then('the audit should record "evidence_stage" as "oracle_comparison"')
def step_audit_stage_b(context) -> None:
    assert any(
        e.get("event") == "evidence_stage" and e.get("stage") == "oracle_comparison"
        for e in context.audit_events
    ), context.audit_events
