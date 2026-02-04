from __future__ import annotations

from behave import given, when, then

from praevisio.infrastructure.rbac import EvidenceAccessService, RbacAuditLog


@given('users "analyst", "counsel", and "auditor"')
def step_users(context) -> None:
    context.users = ["analyst", "counsel", "auditor"]


@given("RBAC is enabled")
def step_rbac_enabled(context) -> None:
    context.audit_log = RbacAuditLog()
    context.rbac_service = EvidenceAccessService(context.audit_log)


@given("an evaluation run has produced artifacts")
def step_artifacts(context) -> None:
    context.artifacts = {
        "evidence": "raw evidence payload",
        "audit": "audit.json",
        "report": "report.json",
    }


@when('"analyst" requests the evidence bundle')
def step_analyst_bundle(context) -> None:
    context.response = context.rbac_service.request_evidence_bundle(
        "analyst", context.artifacts
    )


@then("access should be granted")
def step_access_granted(context) -> None:
    assert context.response.get("granted") is True, context.response


@when('"auditor" requests raw evidence')
def step_auditor_raw(context) -> None:
    context.response = context.rbac_service.request_raw_evidence(
        "auditor", context.artifacts
    )


@then("access should be denied")
def step_access_denied(context) -> None:
    assert context.response.get("granted") is False, context.response


@then('the audit should record an "rbac_denial" entry')
def step_audit_denial(context) -> None:
    assert any(
        entry.get("event_type") == "rbac_denial" and entry.get("user") == "auditor"
        for entry in context.audit_log.entries
    ), context.audit_log.entries


@when('"counsel" requests evidence excerpts')
def step_counsel_excerpts(context) -> None:
    context.response = context.rbac_service.request_evidence_excerpts(
        "counsel", context.artifacts
    )


@then("only redacted excerpts should be returned")
def step_redacted_only(context) -> None:
    excerpts = context.response.get("excerpts", [])
    assert excerpts, context.response
    assert all("REDACTED" in excerpt for excerpt in excerpts), excerpts


@then("the response should include a redaction summary")
def step_redaction_summary(context) -> None:
    summary = context.response.get("redaction_summary")
    assert summary and "redactions" in summary, context.response
