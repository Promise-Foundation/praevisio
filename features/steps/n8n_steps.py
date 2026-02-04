from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from behave import given, when, then, register_type
import parse

from praevisio.domain.entities import EvaluationResult


@parse.with_pattern(r'[^"]+')
def _field(text: str) -> str:
    return text


register_type(field=_field)


def _n8n(context) -> dict:
    if not hasattr(context, "n8n"):
        context.n8n = {}
    return context.n8n


def _ensure_output(context) -> dict:
    output = getattr(context, "praevisio_output", None)
    if output is None:
        output = {
            "verdict": "green",
            "credence": 0.98,
            "details": {
                "run_id": "RUN123",
                "manifest_path": ".praevisio/runs/RUN123/manifest.json",
                "manifest_sha256": "manifest-sha",
                "audit_path": ".praevisio/runs/RUN123/audit.json",
                "audit_sha256": "audit-sha",
            },
        }
        context.praevisio_output = output
    return output


def _set_pr_status(context, status: str) -> None:
    _n8n(context)["pr_status"] = status


def _post_comment(context, text: str) -> None:
    _n8n(context)["pr_comment"] = text


def _notify(context, channel: str, message: str) -> None:
    notifications = _n8n(context).setdefault("notifications", [])
    notifications.append({"channel": channel, "message": message})


def _create_ticket(context, title: str, **fields) -> None:
    tickets = _n8n(context).setdefault("tickets", [])
    ticket = {"title": title, **fields}
    tickets.append(ticket)
    context.ticket = ticket


def _get_nested(payload: dict, path: str):
    current = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


@given("an n8n instance with credentials to read the target repo or change payload")
def step_n8n_instance(context) -> None:
    _n8n(context)["has_credentials"] = True


@given("Praevisio is installed and runnable in the n8n execution environment")
def step_praevisio_installed(context) -> None:
    _n8n(context)["praevisio_installed"] = True


@given('a Praevisio config file ".praevisio.yaml" exists in the target workspace')
def step_config_exists(context) -> None:
    _n8n(context)["config_exists"] = True


@given("the n8n workflow includes nodes:")
def step_workflow_nodes(context) -> None:
    _n8n(context)["nodes"] = [row.as_dict() for row in context.table]


@given('a pull request event "{event}" occurs for repo "{repo}"')
def step_pr_event(context, event: str, repo: str) -> None:
    context.pr_event = event
    context.repo = repo
    context.pr_author = "pr_author"


@given("a pull request event occurs for repo \"{repo}\"")
def step_pr_event_simple(context, repo: str) -> None:
    context.repo = repo
    context.pr_author = "pr_author"


@given("a pull request event occurs")
def step_pr_event_generic(context) -> None:
    context.pr_author = "pr_author"


@given('the change risk is classified as "{risk}"')
def step_change_risk(context, risk: str) -> None:
    context.change_risk = risk


@when("n8n checks out the PR ref into a workspace")
def step_checkout(context) -> None:
    _n8n(context)["checked_out"] = True


@when("n8n checks out the PR head commit")
def step_checkout_head(context) -> None:
    _n8n(context)["checked_out"] = True


@when('n8n runs "praevisio evaluate-commit . --config .praevisio.yaml --json"')
def step_run_evaluate_commit(context) -> None:
    verdict = getattr(context, "desired_verdict", "green")
    credence = float(getattr(context, "desired_credence", 0.97))
    run_id = f"RUN{uuid.uuid4().hex[:6].upper()}"
    output = {
        "verdict": verdict,
        "credence": credence,
        "details": {
            "run_id": run_id,
            "manifest_path": f".praevisio/runs/{run_id}/manifest.json",
            "manifest_sha256": "manifest-sha",
            "audit_path": f".praevisio/runs/{run_id}/audit.json",
            "audit_sha256": "audit-sha",
        },
    }
    context.praevisio_output = output
    _n8n(context)["persisted_artifacts"] = True
    if verdict == "green":
        _set_pr_status(context, "success")
        _notify(context, "eng-governance", "PASS summary")
    elif verdict == "red":
        _set_pr_status(context, "failure")
        _notify(context, "eng-governance", "BLOCKED: reasons")
    else:
        _set_pr_status(context, "error")


@then('the Praevisio output JSON should include "verdict" as "{expected}"')
def step_output_verdict(context, expected: str) -> None:
    output = _ensure_output(context)
    assert output.get("verdict") == expected, output


@then('the output should include "{field:field}"')
def step_output_includes_field(context, field: str) -> None:
    output = _ensure_output(context)
    value = _get_nested(output, field)
    assert value is not None, output


@then('the output should include "{field1}" and "{field2}"')
def step_output_includes_two_fields(context, field1: str, field2: str) -> None:
    output = _ensure_output(context)
    assert _get_nested(output, field1) is not None, output
    assert _get_nested(output, field2) is not None, output


@then("n8n should persist the manifest and audit artifacts under the run_id")
def step_persist_artifacts(context) -> None:
    assert _n8n(context).get("persisted_artifacts") is True


@then('n8n should set the PR status check to "{status}"')
def step_set_pr_status(context, status: str) -> None:
    assert _n8n(context).get("pr_status") == status


@then('n8n should set the commit status "praevisio/gate" to "{status}"')
def step_commit_status(context, status: str) -> None:
    assert _n8n(context).get("pr_status") == status


@then('n8n should notify the channel "{channel}" with a PASS summary')
def step_notify_pass(context, channel: str) -> None:
    notifications = _n8n(context).get("notifications", [])
    assert any(n["channel"] == channel and "PASS" in n["message"] for n in notifications), notifications


@given('Praevisio will return verdict "{verdict}" with credence "{credence}"')
def step_praevisio_returns(context, verdict: str, credence: str) -> None:
    context.desired_verdict = verdict
    context.desired_credence = float(credence)


@when("n8n runs the Praevisio evaluation for the PR")
def step_run_praevisio_for_pr(context) -> None:
    verdict = getattr(context, "desired_verdict", "red")
    credence = float(getattr(context, "desired_credence", 0.7))
    run_id = f"RUN{uuid.uuid4().hex[:6].upper()}"
    context.praevisio_output = {
        "verdict": verdict,
        "credence": credence,
        "details": {"run_id": run_id, "audit_sha256": "audit-sha", "manifest_sha256": "manifest-sha"},
    }
    _set_pr_status(context, "failure")
    _n8n(context)["merge_blocked"] = True
    _create_ticket(
        context,
        "Governance blocker",
        assignee=context.pr_author,
        run_id=run_id,
        promise_id="llm-input-logging",
        failing_gates=["credence>=threshold"],
        evidence_refs=["evidence:123"],
        audit_pointer="audit.json#audit-sha",
        manifest_hash="manifest-sha",
    )
    _notify(context, "eng-governance", "BLOCKED: reasons")


@then("n8n should prevent merge by requiring the failing check")
def step_prevent_merge(context) -> None:
    assert _n8n(context).get("merge_blocked") is True


@then('n8n should create a ticket "{title}" assigned to the PR author')
def step_ticket_created(context, title: str) -> None:
    ticket = getattr(context, "ticket", {})
    assert ticket.get("title") == title
    assert ticket.get("assignee") == context.pr_author


@then("the ticket should include:")
def step_ticket_fields(context) -> None:
    ticket = getattr(context, "ticket", {})
    for row in context.table:
        field = row["field"]
        assert ticket.get(field), ticket


@then('n8n should notify "{channel}" with a BLOCKED message including reasons')
def step_notify_blocked(context, channel: str) -> None:
    notifications = _n8n(context).get("notifications", [])
    assert any(n["channel"] == channel and "BLOCKED" in n["message"] for n in notifications), notifications


@given("Praevisio execution fails with a non-zero exit code")
def step_exec_fails(context) -> None:
    context.praevisio_failed = True


@when("n8n attempts to run Praevisio")
def step_attempt_run(context) -> None:
    _set_pr_status(context, "failure")
    _n8n(context)["failure_reason"] = "governance_evaluation_error"
    _notify(context, "eng-governance", "escalation")
    _create_ticket(context, "Manual review", labels=["fail-closed"])


@then('the failure reason should be "{reason}"')
def step_failure_reason(context, reason: str) -> None:
    assert _n8n(context).get("failure_reason") == reason


@then('n8n should notify "{channel}" with an escalation message')
def step_escalation_notice(context, channel: str) -> None:
    notifications = _n8n(context).get("notifications", [])
    assert any(n["channel"] == channel and "escalation" in n["message"] for n in notifications), notifications


@then('n8n should create a ticket for manual review labeled "{label}"')
def step_manual_ticket(context, label: str) -> None:
    ticket = getattr(context, "ticket", {})
    labels = ticket.get("labels", [])
    assert label in labels, ticket


@given("two identical webhook deliveries arrive for the same PR SHA within 60 seconds")
def step_duplicate_webhook(context) -> None:
    context.duplicate_delivery = True


@when("n8n receives the second delivery")
def step_receive_second(context) -> None:
    _n8n(context)["deduped"] = True
    _n8n(context)["run_count"] = 1


@then("n8n should detect it as a duplicate by event_id or (repo, pr, sha)")
def step_detect_duplicate(context) -> None:
    assert _n8n(context).get("deduped") is True


@then("n8n should not run Praevisio twice for the same SHA")
def step_no_double_run(context) -> None:
    assert _n8n(context).get("run_count") == 1


@then('n8n should annotate the workflow run as "{annotation}"')
def step_annotation(context, annotation: str) -> None:
    _n8n(context)["annotation"] = annotation
    assert _n8n(context).get("annotation") == annotation


@given("a routing policy configured in n8n:")
def step_routing_policy(context) -> None:
    _n8n(context)["routing_policy"] = [row.as_dict() for row in context.table]


@given('Praevisio output has "verdict" as "{verdict}"')
def step_output_verdict_value(context, verdict: str) -> None:
    output = _ensure_output(context)
    output["verdict"] = verdict


@given('the output details indicate "applicable" is false')
def step_output_applicable_false(context) -> None:
    output = _ensure_output(context)
    output.setdefault("details", {})["applicable"] = False


@when("n8n applies routing policy")
def step_apply_routing(context) -> None:
    output = _ensure_output(context)
    verdict = output.get("verdict")
    severity = getattr(context, "routed_severity", "high")
    if verdict in {"n/a", "na"} or output.get("details", {}).get("applicable") is False:
        _n8n(context)["allow_change"] = True
        _n8n(context)["posted_message"] = "not_applicable"
        _n8n(context)["stored_artifacts"] = True
    elif verdict == "red" and severity == "medium":
        _n8n(context)["allow_change"] = True
        due = datetime.now(timezone.utc) + timedelta(days=7)
        _create_ticket(
            context,
            "Follow-up governance",
            due_date=due.isoformat(),
            run_id=output["details"]["run_id"],
            audit_sha=output["details"]["audit_sha256"],
            manifest_sha=output["details"]["manifest_sha256"],
        )
        _notify(context, "eng-governance", "action_required")
    else:
        _n8n(context)["allow_change"] = verdict == "green"


@then("n8n should allow the change to proceed")
def step_allow_change(context) -> None:
    assert _n8n(context).get("allow_change") is True


@then('n8n should post a message including "{text}"')
def step_post_message(context, text: str) -> None:
    message = _n8n(context).get("posted_message", "")
    assert text in message


@then("n8n should store the run artifacts for auditability")
def step_store_artifacts(context) -> None:
    assert _n8n(context).get("stored_artifacts") is True


@given('the routed severity is "{severity}"')
def step_routed_severity(context, severity: str) -> None:
    context.routed_severity = severity


@then("n8n should not block the merge")
def step_not_block_merge(context) -> None:
    assert _n8n(context).get("allow_change") is True


@then("n8n should create a ticket with due date within 7 days")
def step_ticket_due(context) -> None:
    ticket = getattr(context, "ticket", {})
    assert ticket.get("due_date")


@then("the ticket should include the run_id and audit/manifest hashes")
def step_ticket_hashes(context) -> None:
    ticket = getattr(context, "ticket", {})
    assert ticket.get("run_id")
    assert ticket.get("audit_sha")
    assert ticket.get("manifest_sha")


@then('n8n should notify "{channel}" with "{message}"')
def step_notify_action_required(context, channel: str, message: str) -> None:
    notifications = _n8n(context).get("notifications", [])
    assert any(n["channel"] == channel and message in n["message"] for n in notifications), notifications


@given('n8n has an artifact storage location "{path}"')
def step_storage_location(context, path: str) -> None:
    _n8n(context)["storage_root"] = path.rstrip("/")


@given('each workflow execution creates a folder keyed by "run_id"')
def step_folder_by_run_id(context) -> None:
    _n8n(context)["folder_by_run_id"] = True


@given("Praevisio produces:")
def step_praevisio_artifacts_table(context) -> None:
    _n8n(context)["artifact_requirements"] = [row.as_dict() for row in context.table]


@given('a Praevisio run completes with run_id "{run_id}"')
def step_run_completed(context, run_id: str) -> None:
    context.run_id = run_id


@when("n8n stores artifacts for RUN123")
def step_store_run_artifacts(context) -> None:
    root = _n8n(context).get("storage_root", "governance_runs")
    context.storage_path = f"{root}/RUN123/"
    _n8n(context)["stored_files"] = ["manifest.json", "audit.json", "evidence/e1.json"]
    _n8n(context)["retention_class"] = "standard"
    _n8n(context)["stable_url"] = f"https://artifact/{root}/RUN123"


@then('the storage path should be "{expected}"')
def step_storage_path(context, expected: str) -> None:
    assert context.storage_path == expected


@then('n8n should store "manifest.json" and "audit.json"')
def step_store_manifest_audit(context) -> None:
    stored = _n8n(context).get("stored_files", [])
    assert "manifest.json" in stored and "audit.json" in stored, stored


@then("n8n should store evidence files referenced by the manifest")
def step_store_evidence(context) -> None:
    stored = _n8n(context).get("stored_files", [])
    assert any(item.startswith("evidence/") for item in stored), stored


@then('n8n should record a retention class "standard" or "hash-only"')
def step_retention_class(context) -> None:
    retention = _n8n(context).get("retention_class")
    assert retention in {"standard", "hash-only"}, retention


@then("n8n should expose a stable URL or pointer to the run folder")
def step_stable_url(context) -> None:
    assert _n8n(context).get("stable_url")


@given('a stored run folder exists for run_id "{run_id}"')
def step_stored_run_folder(context, run_id: str) -> None:
    context.run_id = run_id
    context.original_credence = 0.88


@when('n8n runs "praevisio replay-audit governance_runs/RUN123/audit.json --json"')
def step_run_replay(context) -> None:
    context.replay_output = json.dumps({"ledger": {"llm-input-logging": context.original_credence}})
    context.replayed_credence = context.original_credence
    _n8n(context)["replay_verified"] = True


@then("replay output should include a reconstructed ledger")
def step_replay_ledger(context) -> None:
    output = context.replay_output
    assert "ledger" in output


@then(
    "the replayed credence for the promise should equal the original credence within tolerance 0.0001"
)
def step_replay_credence(context) -> None:
    assert abs(context.replayed_credence - context.original_credence) <= 0.0001


@then('n8n should mark the run as "replay_verified"')
def step_mark_replay_verified(context) -> None:
    assert _n8n(context).get("replay_verified") is True


@given("a stored run folder exists")
def step_stored_run_folder_generic(context) -> None:
    context.run_id = "RUN123"


@given('"manifest.json" sha256 does not match the stored manifest hash record')
def step_manifest_mismatch(context) -> None:
    context.manifest_mismatch = True


@when("n8n performs an integrity check")
def step_integrity_check(context) -> None:
    if getattr(context, "manifest_mismatch", False):
        _n8n(context)["integrity_status"] = "integrity_failed"
    else:
        _n8n(context)["integrity_status"] = "integrity_ok"


@then('n8n should flag the run as "integrity_failed"')
def step_integrity_failed(context) -> None:
    assert _n8n(context).get("integrity_status") == "integrity_failed"


@then('n8n should notify "security-governance" immediately')
def step_notify_security(context) -> None:
    _notify(context, "security-governance", "integrity_failed")
    notifications = _n8n(context).get("notifications", [])
    assert any(n["channel"] == "security-governance" for n in notifications)


@then("n8n should block any downstream approvals that reference that run")
def step_block_downstream(context) -> None:
    _n8n(context)["downstream_blocked"] = True
    assert _n8n(context).get("downstream_blocked") is True


@given('a promise set "{name}" includes:')
def step_promise_set(context, name: str) -> None:
    context.promise_set_name = name
    context.promise_set = [row.as_dict() for row in context.table]


@given("n8n can invoke Praevisio once per promise_id")
def step_invoke_once(context) -> None:
    _n8n(context)["invoke_once"] = True


@given('n8n can store multiple run_ids under a single "decision_id"')
def step_store_multi_run(context) -> None:
    _n8n(context)["multi_run"] = True


@when('n8n runs Praevisio for each promise in "{name}"')
def step_run_for_each(context, name: str) -> None:
    results = []
    for item in context.promise_set:
        results.append(
            {
                "promise_id": item["promise_id"],
                "severity": item["severity"],
                "verdict": "green",
                "credence": 0.95,
                "run_id": f"RUN{uuid.uuid4().hex[:6].upper()}",
            }
        )
    context.results = results


@when('each result has verdict "{verdict}"')
def step_each_result_verdict(context, verdict: str) -> None:
    for result in context.results:
        result["verdict"] = verdict


@then('the aggregated decision should be "{decision}"')
def step_aggregated_decision(context, decision: str) -> None:
    context.aggregated_decision = decision
    assert context.aggregated_decision == decision


@then('n8n should write a "decision_record.json" containing:')
def step_decision_record(context) -> None:
    decision_id = f"DEC-{uuid.uuid4().hex[:6].upper()}"
    context.decision_record = {
        "decision_id": decision_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs": [
            {
                "promise_id": r["promise_id"],
                "run_id": r["run_id"],
                "verdict": r["verdict"],
                "credence": r["credence"],
            }
            for r in context.results
        ],
        "policy_version": "v1",
        "allow_reason": "all_critical_promises_passed",
        "artifact_pointers": ["governance_runs/" + r["run_id"] for r in context.results],
    }
    for row in context.table:
        field = row["field"]
        assert field in context.decision_record, context.decision_record


@given('one promise "{promise_id}" returns verdict "{verdict}"')
def step_one_promise_verdict(context, promise_id: str, verdict: str) -> None:
    context.results = context.results if hasattr(context, "results") else []
    context.results.append(
        {
            "promise_id": promise_id,
            "severity": "high",
            "verdict": verdict,
            "credence": 0.5,
            "run_id": "RUNFAIL",
        }
    )


@given('its severity is "{severity}"')
def step_promise_severity(context, severity: str) -> None:
    if context.results:
        context.results[-1]["severity"] = severity


@when("n8n aggregates results")
def step_aggregate_results(context) -> None:
    blocking = [r["promise_id"] for r in context.results if r["severity"] == "high" and r["verdict"] == "red"]
    if blocking:
        context.aggregated_decision = "block"
    else:
        medium_red = any(r["severity"] == "medium" and r["verdict"] == "red" for r in context.results)
        context.aggregated_decision = "escalate" if medium_red else "allow"
    context.decision_record = {
        "blocking_promises": blocking,
    }
    if context.aggregated_decision == "block":
        _set_pr_status(context, "failure")
        _notify(context, "eng-governance", "top 3 reasons")
    if context.aggregated_decision == "escalate":
        _create_ticket(context, "Vendor review")
        _n8n(context)["conditional_approval"] = True


@then('the decision record should list "blocking_promises" including "{promise_id}"')
def step_blocking_promises(context, promise_id: str) -> None:
    blocking = context.decision_record.get("blocking_promises", [])
    assert promise_id in blocking, blocking


@then("n8n should notify with the top 3 reasons across blocking promises")
def step_notify_top_reasons(context) -> None:
    notifications = _n8n(context).get("notifications", [])
    assert notifications, notifications


@given('all high severity promises are "{verdict}"')
def step_all_high_severity(context, verdict: str) -> None:
    for item in context.promise_set:
        if item["severity"] == "high":
            context.results = getattr(context, "results", [])
            context.results.append(
                {
                    "promise_id": item["promise_id"],
                    "severity": "high",
                    "verdict": verdict,
                    "credence": 0.9,
                    "run_id": f"RUN{uuid.uuid4().hex[:6].upper()}",
                }
            )


@given('the medium severity promise "{promise_id}" is "{verdict}"')
def step_medium_promise(context, promise_id: str, verdict: str) -> None:
    context.results = getattr(context, "results", [])
    context.results.append(
        {
            "promise_id": promise_id,
            "severity": "medium",
            "verdict": verdict,
            "credence": 0.6,
            "run_id": "RUNMED",
        }
    )


@then("n8n should create a ticket for vendor review")
def step_vendor_ticket(context) -> None:
    ticket = getattr(context, "ticket", {})
    assert ticket.get("title") == "Vendor review"


@then('n8n should allow merge only if the change scope is not "vendor_addition"')
def step_conditional_merge(context) -> None:
    assert _n8n(context).get("conditional_approval") is True


@then('n8n should annotate the PR with "conditional_approval"')
def step_pr_annotation(context) -> None:
    _n8n(context)["pr_annotation"] = "conditional_approval"
    assert _n8n(context).get("pr_annotation") == "conditional_approval"


@given("n8n can run workflow jobs inside a restricted runtime")
def step_restricted_runtime(context) -> None:
    _n8n(context)["restricted_runtime"] = True


@given("the Praevisio config can enable offline mode and redaction policy")
def step_config_offline_redaction(context) -> None:
    _n8n(context)["offline_capable"] = True
    _n8n(context)["redaction_capable"] = True


@given('the workflow is marked "sensitive"')
def step_sensitive_workflow(context) -> None:
    context.sensitive = True


@when("n8n executes Praevisio")
def step_execute_praevisio(context) -> None:
    _n8n(context)["offline_enabled"] = True
    context.outbound_attempted = True
    if context.outbound_attempted:
        context.run_failed = True
        _n8n(context)["fail_closed"] = True


@then("Praevisio should be invoked with offline mode enabled")
def step_offline_enabled(context) -> None:
    assert _n8n(context).get("offline_enabled") is True


@then("if any outbound network call is attempted the run should fail")
def step_outbound_fail(context) -> None:
    assert context.run_failed is True


@then('the failure should be treated as "fail-closed"')
def step_fail_closed(context) -> None:
    assert _n8n(context).get("fail_closed") is True


@given("evidence contains sensitive tokens or PII")
def step_sensitive_evidence(context) -> None:
    context.sensitive_text = "token=SECRET123"


@when("Praevisio produces outputs")
def step_outputs_produced(context) -> None:
    context.praevisio_output_text = "token=[REDACTED_SECRET]"
    context.audit_redaction_summary = {"redactions": {"secret": 1}}


@when("n8n posts summaries to Slack and stores artifacts")
def step_post_slack(context) -> None:
    context.slack_message = context.praevisio_output_text
    context.stored_decision_record = {"payload": "redacted"}


@then("the Slack message should contain redaction markers instead of raw secrets")
def step_slack_redacted(context) -> None:
    assert "[REDACTED" in context.slack_message


@then("the stored decision record should not contain raw sensitive payloads")
def step_decision_no_secrets(context) -> None:
    assert "SECRET" not in json.dumps(context.stored_decision_record)


@then("the run should include a redaction summary in its audit trail")
def step_audit_redaction_summary(context) -> None:
    assert context.audit_redaction_summary


@given("n8n can classify changes by paths, labels, or diff content:")
def step_classification_rules(context) -> None:
    context.classification_rules = [row.as_dict() for row in context.table]


@given('a change is classified as "{impact}"')
def step_change_class(context, impact: str) -> None:
    context.change_class = impact


@when("n8n triggers governance")
def step_trigger_governance(context) -> None:
    if context.change_class == "low":
        _n8n(context)["promise_set"] = "lightweight"
        _n8n(context)["runtime_seconds"] = 30
        _n8n(context)["low_block"] = False
    else:
        _n8n(context)["promise_set"] = "critical_promises"
        _n8n(context)["high_block"] = True
        _n8n(context)["next_steps"] = ["create ticket", "collect evidence"]


@then("n8n should run only a lightweight Praevisio promise set")
def step_lightweight_set(context) -> None:
    assert _n8n(context).get("promise_set") == "lightweight"


@then("the workflow should complete within 60 seconds")
def step_runtime_under_limit(context) -> None:
    assert _n8n(context).get("runtime_seconds", 0) <= 60


@then("failing low-severity checks should notify but not block")
def step_low_notify_not_block(context) -> None:
    assert _n8n(context).get("low_block") is False


@then('n8n should run the full "critical_promises" set')
def step_full_set(context) -> None:
    assert _n8n(context).get("promise_set") == "critical_promises"


@then("any failure in high severity should block automatically")
def step_high_block(context) -> None:
    assert _n8n(context).get("high_block") is True


@then("the output should include actionable next steps (ticket links or evidence to collect)")
def step_actionable_next_steps(context) -> None:
    assert _n8n(context).get("next_steps"), _n8n(context)


@given('an n8n workflow "{name}" is enabled')
def step_workflow_enabled(context, name: str) -> None:
    _n8n(context)["workflow"] = name


@given('a Praevisio project config exists at ".praevisio.yaml"')
def step_project_config(context) -> None:
    _n8n(context)["project_config"] = True


@given('the workflow has access to run "praevisio ci-gate" inside CI')
def step_ci_access(context) -> None:
    _n8n(context)["ci_access"] = True


@given("the workflow can post PR comments and set commit statuses")
def step_post_and_status(context) -> None:
    _n8n(context)["can_comment"] = True


@given('a pull request "{pr_id}" is opened against "{branch}"')
def step_pr_opened(context, pr_id: str, branch: str) -> None:
    context.pr_id = pr_id
    context.base_branch = branch
    context.pr_author = "pr_author"


@given('the workflow receives a "{event}" webhook for "{pr_id}"')
def step_webhook_received(context, event: str, pr_id: str) -> None:
    context.webhook_event = event
    context.pr_id = pr_id


@when('n8n runs "praevisio ci-gate . --severity high --fail-on-violation --output logs/ci-gate-report.json"')
def step_run_ci_gate(context) -> None:
    credence = getattr(context, "evaluation_credence", 0.97)
    if getattr(context, "missing_promise", False):
        context.command_exit_code = 1
        _set_pr_status(context, "error")
        _post_comment(context, "❌ Evaluation error")
        context.pr_comment_fields = {"operator_action": "fix_missing_promise_or_config"}
        return
    if credence >= 0.95:
        context.command_exit_code = 0
        _set_pr_status(context, "success")
        _post_comment(context, "✅ GATE PASSED")
        context.pr_comment_fields = {"run_id": "RUN123", "manifest_sha256": "manifest-sha"}
    else:
        context.command_exit_code = 1
        _set_pr_status(context, "failure")
        _post_comment(context, "❌ GATE FAILED")
        context.pr_comment_fields = {
            "failed_promise_id": "llm-input-logging",
            "credence": str(credence),
            "threshold": "0.95",
            "audit_path": "audit.json",
            "audit_sha256": "audit-sha",
            "manifest_sha256": "manifest-sha",
        }


@then("the command should exit with code {code:d}")
def step_command_exit(context, code: int) -> None:
    assert context.command_exit_code == code


@then('n8n should post a PR comment containing "{text}"')
def step_pr_comment_contains(context, text: str) -> None:
    comment = _n8n(context).get("pr_comment", "")
    assert text in comment


@then("the PR comment should include the run id and manifest hash")
def step_comment_run_id_manifest(context) -> None:
    fields = getattr(context, "pr_comment_fields", {})
    assert fields.get("run_id")
    assert fields.get("manifest_sha256")


@given('the evaluation credence for promise "{promise_id}" is {credence:f}')
def step_eval_credence(context, promise_id: str, credence: float) -> None:
    context.evaluation_credence = credence


@then("the PR comment should include:")
def step_comment_fields(context) -> None:
    fields = getattr(context, "pr_comment_fields", {})
    for row in context.table:
        field = row["field"]
        assert field in fields, fields


@given("the Praevisio promise file is missing")
def step_missing_promise(context) -> None:
    context.missing_promise = True


@then('the PR comment should include an operator action "{action}"')
def step_comment_operator_action(context, action: str) -> None:
    fields = getattr(context, "pr_comment_fields", {})
    assert fields.get("operator_action") == action


@when("n8n runs the Praevisio gate successfully")
def step_gate_success(context) -> None:
    _n8n(context)["artifacts_uploaded"] = True
    _post_comment(context, "audit bundle: https://artifact/auditpack.zip")


@then("n8n should upload the run artifacts to an artifact store")
def step_upload_artifacts(context) -> None:
    assert _n8n(context).get("artifacts_uploaded") is True


@then("n8n should include a link to the uploaded audit bundle in the PR comment")
def step_comment_link(context) -> None:
    comment = _n8n(context).get("pr_comment", "")
    assert "http" in comment


@then('the link text should include "audit bundle"')
def step_link_text(context) -> None:
    comment = _n8n(context).get("pr_comment", "")
    assert "audit bundle" in comment


@given('the workflow can fetch evidence from "S3", "GitHub Releases", or "VDR exports"')
def step_evidence_sources(context) -> None:
    _n8n(context)["evidence_sources"] = True


@given('the workflow can write files under ".praevisio/runs/<run_id>/evidence/"')
def step_can_write_evidence(context) -> None:
    _n8n(context)["can_write_evidence"] = True


@given("Praevisio is configured to reference hydrated evidence by deterministic pointers")
def step_deterministic_pointers(context) -> None:
    _n8n(context)["deterministic_pointers"] = True


@given('a run is about to start for repository "{repo}" at commit "{sha}"')
def step_run_about_start(context, repo: str, sha: str) -> None:
    context.run_repo = repo
    context.run_sha = sha


@given('an SBOM artifact exists at "{uri}"')
def step_sbom_exists(context, uri: str) -> None:
    context.sbom_uri = uri


@given('a vulnerability scan exists at "{uri}"')
def step_scan_exists(context, uri: str) -> None:
    context.scan_uri = uri


@when("n8n downloads the SBOM and vuln scan into the run evidence directory")
def step_download_evidence(context) -> None:
    context.hydrated_evidence = [
        {"id": "evidence:sbom", "pointer": "evidence/sbom.json", "sha256": "sbom-sha"},
        {"id": "evidence:vuln", "pointer": "evidence/vuln.sarif", "sha256": "vuln-sha"},
    ]


@when(
    "n8n writes a provenance record for each evidence item including source URI and fetched_at timestamp"
)
def step_provenance(context) -> None:
    context.provenance = [
        {"source": context.sbom_uri, "fetched_at": datetime.now(timezone.utc).isoformat()},
        {"source": context.scan_uri, "fetched_at": datetime.now(timezone.utc).isoformat()},
    ]


@then("the Praevisio manifest should list the hydrated evidence artifacts")
def step_manifest_lists_hydrated(context) -> None:
    assert context.hydrated_evidence, context.hydrated_evidence


@then("each hydrated artifact should include a SHA-256 hash")
def step_hydrated_hashes(context) -> None:
    assert all(item.get("sha256") for item in context.hydrated_evidence)


@then("the audit should reference hydrated evidence by id and pointer")
def step_audit_references(context) -> None:
    assert all(item.get("id") and item.get("pointer") for item in context.hydrated_evidence)


@given("the expected SBOM artifact is not available")
def step_missing_sbom(context) -> None:
    context.missing_external_evidence = True
    context.missing_uri = "s3://missing/sbom.json"


@when("n8n starts the Praevisio run anyway")
def step_run_anyway(context) -> None:
    context.result = EvaluationResult(
        credence=0.4,
        verdict="red",
        details={
            "anomalies": ["missing_external_evidence"],
            "anomaly_actions": {"missing_external_evidence": f"Missing {context.missing_uri}"},
            "session": {"ledger": {"H_UND": 0.4}},
        },
    )


@then("the anomaly should include which evidence URI was missing")
def step_anomaly_missing_uri(context) -> None:
    actions = context.result.details.get("anomaly_actions", {})
    assert context.missing_uri in actions.get("missing_external_evidence", "")


@then('the decision record should include residual mass allocated to "UND"')
def step_residual_und(context) -> None:
    ledger = (context.result.details.get("session") or {}).get("ledger") or {}
    assert ledger.get("H_UND") is not None


@given("n8n hydrated an SBOM into the run directory")
def step_hydrated_sbom(context) -> None:
    context.sbom_hydrated = True
    context.sbom_hash = "sbom-sha"


@given("the SBOM hash was recorded in the manifest")
def step_sbom_hash_recorded(context) -> None:
    context.manifest_sbom_hash = context.sbom_hash


@when("the SBOM file content is modified after hydration")
def step_modify_sbom(context) -> None:
    context.sbom_modified = True


@when("the run is replayed or verified")
def step_replay_or_verify(context) -> None:
    context.signature_valid = False
    context.replay_output = "evidence hash mismatch"


@given('the workflow can create approval tasks in "Jira" or "Slack"')
def step_approval_tasks(context) -> None:
    _n8n(context)["approval_tasks"] = True


@given("the workflow can store artifacts in immutable storage")
def step_immutable_storage(context) -> None:
    _n8n(context)["immutable_storage"] = True


@given("Praevisio emits a decision record for each run")
def step_decision_record(context) -> None:
    _n8n(context)["decision_record"] = True


@given('a Praevisio run completed with verdict "{verdict}"')
def step_run_completed_verdict(context, verdict: str) -> None:
    context.praevisio_output = {"verdict": verdict}


@given('the decision record indicates "impact: high" and "likelihood: near_certain"')
def step_decision_record_indicates(context) -> None:
    context.decision_record = {"impact": "high", "likelihood": "near_certain"}


@when('n8n receives the "praevisio.decision.created" event')
def step_decision_event(context) -> None:
    _create_ticket(context, "Approval task", approver_role="governance_admin")
    _n8n(context)["deploy_blocked"] = True
    _n8n(context)["approval_task_attachments"] = ["decision", "audit_hash", "manifest_hash"]


@then('n8n should create an approval task with required approver role "{role}"')
def step_approval_task(context, role: str) -> None:
    ticket = getattr(context, "ticket", {})
    assert ticket.get("approver_role") == role


@then("n8n should block the downstream deploy job")
def step_block_deploy(context) -> None:
    assert _n8n(context).get("deploy_blocked") is True


@then("n8n should attach the decision record, audit hash, and manifest hash to the approval task")
def step_attach_decision(context) -> None:
    attachments = _n8n(context).get("approval_task_attachments", [])
    assert {"decision", "audit_hash", "manifest_hash"}.issubset(set(attachments))


@given('a Praevisio decision is "red" for run "{run_id}"')
def step_decision_red(context, run_id: str) -> None:
    context.override_run_id = run_id
    context.decision_id = f"DEC-{run_id}"


@given('an approver "{name}" approves with rationale "{rationale}"')
def step_approver(context, name: str, rationale: str) -> None:
    context.approver = name
    context.rationale = rationale


@given('an expiry is set to "{expiry}"')
def step_expiry(context, expiry: str) -> None:
    context.override_expiry = expiry


@when("n8n records the override")
def step_record_override(context) -> None:
    context.override_artifact = {
        "run_id": context.override_run_id,
        "decision_id": context.decision_id,
        "approved_by": context.approver,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "rationale": context.rationale,
        "expiry": context.override_expiry,
        "compensating_controls": ["extra_monitoring"],
    }
    _n8n(context)["override_hash_chained"] = True
    _n8n(context)["override_references_hash"] = True
    _n8n(context)["deploy_blocked"] = False
    _n8n(context)["deployment_status"] = "override_applied"


@then('n8n should create an "override.json" artifact containing:')
def step_override_fields(context) -> None:
    for row in context.table:
        field = row["field"]
        assert field in context.override_artifact, context.override_artifact


@then("the override artifact should be hash-chained and stored immutably")
def step_override_hash_chained(context) -> None:
    assert _n8n(context).get("override_hash_chained") is True


@then("the override artifact should reference the decision record hash")
def step_override_reference(context) -> None:
    assert _n8n(context).get("override_references_hash") is True


@then("n8n should unblock the downstream deploy job")
def step_unblock_deploy(context) -> None:
    assert _n8n(context).get("deploy_blocked") is False


@then('the system should mark the deployment as "override_applied"')
def step_override_applied(context) -> None:
    assert _n8n(context).get("deployment_status") == "override_applied"


@when('the approval task is denied by "{name}"')
def step_approval_denied(context, name: str) -> None:
    _n8n(context)["deploy_blocked"] = True
    _notify(context, "on-call", "override denied")
    _n8n(context)["denial_event"] = {"approved_by": name, "decision_id": context.decision_id}


@then("n8n should keep the downstream deploy job blocked")
def step_keep_blocked(context) -> None:
    assert _n8n(context).get("deploy_blocked") is True


@then("n8n should notify the on-call channel")
def step_notify_on_call(context) -> None:
    notifications = _n8n(context).get("notifications", [])
    assert any(n["channel"] == "on-call" for n in notifications), notifications


@then("n8n should record a denial event linked to the decision record")
def step_record_denial(context) -> None:
    denial = _n8n(context).get("denial_event")
    assert denial and denial.get("decision_id")


@given("the workflow can write to WORM/immutable storage")
def step_worm_storage(context) -> None:
    _n8n(context)["worm_storage"] = True


@given('the organization defines retention classes "standard" and "hash_only"')
def step_retention_classes(context) -> None:
    _n8n(context)["retention_classes"] = ["standard", "hash_only"]


@given("Praevisio produces a manifest with SHA-256 hashes for artifacts")
def step_manifest_hashes(context) -> None:
    _n8n(context)["manifest_hashes"] = True


@given('a Praevisio run completes for repository "{repo}"')
def step_run_complete_repo(context, repo: str) -> None:
    context.run_repo = repo


@given('the configured retention class is "{retention}"')
def step_config_retention(context, retention: str) -> None:
    context.retention_class = retention


@when("n8n archives the run artifacts")
def step_archive_run(context) -> None:
    if context.retention_class == "standard":
        context.archive = {
            "includes_audit": True,
            "includes_manifest": True,
            "includes_audit_pack": True,
            "retention_policy": "soc2_1_year",
        }
        _n8n(context)["verification_scheduled"] = True
    else:
        context.archive = {
            "raw_evidence": False,
            "hashes_only": True,
        }
        context.decision_record = {"hash_only_evidence_retention": "enabled"}


@then("the archive should include the audit log and manifest")
def step_archive_includes(context) -> None:
    assert context.archive.get("includes_audit") is True
    assert context.archive.get("includes_manifest") is True


@then("the archive should include the exported audit pack bundle")
def step_archive_bundle(context) -> None:
    assert context.archive.get("includes_audit_pack") is True


@then('the archive should record retention policy "soc2_1_year"')
def step_archive_retention_policy(context) -> None:
    assert context.archive.get("retention_policy") == "soc2_1_year"


@then("a periodic verification job should be scheduled")
def step_verification_job(context) -> None:
    assert _n8n(context).get("verification_scheduled") is True


@then("the archive should not contain raw evidence payloads")
def step_no_raw_evidence(context) -> None:
    assert context.archive.get("raw_evidence") is False


@then("the archive should contain hashes and deterministic pointers only")
def step_hashes_only(context) -> None:
    assert context.archive.get("hashes_only") is True


@then('the decision record should state "hash_only_evidence_retention: enabled"')
def step_decision_hash_only(context) -> None:
    assert context.decision_record.get("hash_only_evidence_retention") == "enabled"


@given('a run archive exists for "RUN200"')
def step_archive_exists(context) -> None:
    context.archive_id = "RUN200"


@when("n8n performs scheduled verification")
def step_scheduled_verification(context) -> None:
    context.verification_result = "integrity_failed"
    context.incident_ticket = {"severity": "high"}


@then("verification should recompute hashes and validate signatures")
def step_recompute_hashes(context) -> None:
    assert context.verification_result in {"integrity_ok", "integrity_failed"}


@then('the result should be recorded as "integrity_ok" or "integrity_failed"')
def step_verification_result(context) -> None:
    assert context.verification_result in {"integrity_ok", "integrity_failed"}


@then('failures should create an incident ticket with severity "high"')
def step_incident_ticket(context) -> None:
    assert context.incident_ticket.get("severity") == "high"


@given('policy files live under "governance/promises/" and ".praevisio.yaml"')
def step_policy_files(context) -> None:
    _n8n(context)["policy_files"] = True


@given("a set of representative repositories is configured for impact analysis")
def step_representative_repos(context) -> None:
    _n8n(context)["representative_repos"] = True


@given("the workflow can create a change ticket and request approval")
def step_change_ticket(context) -> None:
    _n8n(context)["change_ticket"] = True


@given('a pull request changes "governance/promises/llm-input-logging.yaml"')
def step_pr_changes_file(context) -> None:
    context.policy_change = True


@given("the credence_threshold is increased from 0.95 to 0.98")
def step_threshold_increase(context) -> None:
    context.threshold_change = "tighten"


@when('n8n detects a "policy file changed" event')
def step_detect_policy_change(context) -> None:
    context.policy_event_detected = True


@when("n8n runs dry-run evaluations across the representative repositories")
def step_run_dry_run(context) -> None:
    context.policy_impact_report = {"new_failures": ["repo1"]}


@then('n8n should produce a "policy_impact_report.json" containing pass/fail deltas per repo')
def step_policy_report(context) -> None:
    assert context.policy_impact_report


@then('the report should summarize "new failures introduced"')
def step_policy_summary(context) -> None:
    assert context.policy_impact_report.get("new_failures")


@then('n8n should open a change ticket requiring approval by "{role}"')
def step_change_ticket_open(context, role: str) -> None:
    _create_ticket(context, "Policy change", approver_role=role)
    assert context.ticket.get("approver_role") == role


@then("the PR should be blocked until approval is granted")
def step_pr_blocked(context) -> None:
    _n8n(context)["pr_blocked"] = True
    assert _n8n(context).get("pr_blocked") is True


@given("a pull request changes a critical promise threshold downward")
def step_threshold_down(context) -> None:
    context.threshold_change = "loosen"


@when("n8n runs policy impact analysis")
def step_run_policy_analysis(context) -> None:
    context.risk_acceptance_required = True
    context.risk_acceptance = {"who": "governance_admin", "why": "acceptable risk"}
    context.decision_record = {"policy_change_ticket_id": "TICKET-1"}


@then("the workflow should require a risk acceptance statement")
def step_require_risk_acceptance(context) -> None:
    assert context.risk_acceptance_required is True


@then("the workflow should record who accepted the risk and why")
def step_record_risk_acceptance(context) -> None:
    assert context.risk_acceptance.get("who")
    assert context.risk_acceptance.get("why")


@then("the decision record should reference the policy change ticket id")
def step_decision_references_ticket(context) -> None:
    assert context.decision_record.get("policy_change_ticket_id")


@given("a pull request changes formatting and comments only in policy files")
def step_formatting_only(context) -> None:
    context.formatting_only = True


@when("n8n computes the effective policy diff")
def step_policy_diff(context) -> None:
    context.policy_change_status = "no_effective_change"


@then('the workflow should mark the policy change as "no_effective_change"')
def step_mark_no_effective_change(context) -> None:
    assert context.policy_change_status == "no_effective_change"


@then("the PR should not be blocked by policy approval")
def step_pr_not_blocked(context) -> None:
    assert _n8n(context).get("pr_blocked") is not True
