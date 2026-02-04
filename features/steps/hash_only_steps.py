from __future__ import annotations

import json
from pathlib import Path

from behave import given, when, then
from typer.testing import CliRunner
from praevisio.application.evaluation_service import EvaluationService
from praevisio.domain.evaluation_config import EvaluationConfig


def _hash_only_config() -> EvaluationConfig:
    return EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.2,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        run_dir=".praevisio/runs",
        hash_only_evidence=True,
    )


def _extract_events(audit_payload: object) -> list[dict]:
    if isinstance(audit_payload, dict) and isinstance(audit_payload.get("events"), list):
        return audit_payload["events"]
    if isinstance(audit_payload, list):
        return audit_payload
    return []


def _evidence_items(audit_payload: object) -> list[dict]:
    items: list[dict] = []
    for event in _extract_events(audit_payload):
        payload = event.get("payload") or {}
        if isinstance(payload.get("evidence_items"), list):
            items.extend(payload["evidence_items"])
    return items


@given("hash-only evidence retention is enabled")
def step_hash_only_enabled(context) -> None:
    service = EvaluationService(
        analyzer=context.analyzer,
        test_runner=context.test_runner,
        promise_loader=context.promise_loader,
    )
    result = service.evaluate_path(str(context.repo_path), config=_hash_only_config())
    context.result = result
    details = result.details
    context.audit_path = Path(details["audit_path"])
    context.manifest_path = Path(details["manifest_path"])
    context.runner = getattr(context, "runner", CliRunner())
    context.use_cli_replay = True


@when("I inspect the audit file")
def step_inspect_audit(context) -> None:
    audit_path = getattr(context, "audit_path", None)
    if audit_path is None:
        audit_path = Path(context.result.details["audit_path"])
    context.audit_text = Path(audit_path).read_text(encoding="utf-8")
    context.audit_payload = json.loads(context.audit_text)


@then("each evidence artifact should have a SHA-256 hash")
def step_manifest_hashes(context) -> None:
    manifest_text = getattr(context, "manifest", None)
    if not manifest_text:
        manifest_path = getattr(context, "manifest_path", None)
        manifest_text = Path(manifest_path).read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    artifacts = manifest.get("artifacts", [])
    assert artifacts, "No artifacts listed in manifest"
    for artifact in artifacts:
        assert artifact.get("sha256"), artifact


@then("each evidence artifact should have a deterministic pointer")
def step_manifest_pointers(context) -> None:
    manifest_text = getattr(context, "manifest", None)
    if not manifest_text:
        manifest_path = getattr(context, "manifest_path", None)
        manifest_text = Path(manifest_path).read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    artifacts = manifest.get("artifacts", [])
    assert artifacts, "No artifacts listed in manifest"
    for artifact in artifacts:
        pointer = artifact.get("pointer") or artifact.get("path")
        assert pointer, artifact
        assert not Path(pointer).is_absolute(), pointer


@then("the manifest should not contain raw evidence snippets")
def step_manifest_no_raw(context) -> None:
    manifest_text = getattr(context, "manifest", None)
    if not manifest_text:
        manifest_path = getattr(context, "manifest_path", None)
        manifest_text = Path(manifest_path).read_text(encoding="utf-8")
    raw_markers = ["test_passes", "violations_found", "exit_code", "targets", "args"]
    assert not any(marker in manifest_text for marker in raw_markers), manifest_text


@then('each evidence reference should include "evidence_id"')
def step_audit_evidence_ids(context) -> None:
    audit_payload = getattr(context, "audit_payload", None)
    if audit_payload is None:
        step_inspect_audit(context)
        audit_payload = context.audit_payload
    items = _evidence_items(audit_payload)
    assert items, "No evidence references in audit"
    for item in items:
        assert item.get("evidence_id") or item.get("id"), item


@then('each evidence reference should include "pointer"')
def step_audit_pointers(context) -> None:
    audit_payload = getattr(context, "audit_payload", None)
    if audit_payload is None:
        step_inspect_audit(context)
        audit_payload = context.audit_payload
    items = _evidence_items(audit_payload)
    assert items, "No evidence references in audit"
    for item in items:
        pointer = item.get("pointer")
        if not pointer:
            metadata = item.get("metadata") or {}
            pointer = metadata.get("pointer")
        assert pointer, item


@then("the audit should not include raw evidence payloads")
def step_audit_no_raw(context) -> None:
    audit_text = getattr(context, "audit_text", None)
    if not audit_text:
        step_inspect_audit(context)
        audit_text = context.audit_text
    raw_markers = ["test_passes", "violations_found", "exit_code", "targets", "args"]
    assert not any(marker in audit_text for marker in raw_markers), audit_text


@given("an audit file from a hash-only run")
def step_hash_only_audit(context) -> None:
    audit_path = getattr(context, "audit_path", None)
    if audit_path is None:
        audit_path = Path(context.result.details["audit_path"])
    context.audit_path = Path(audit_path)


@given("the evidence artifacts are missing locally")
def step_evidence_missing(context) -> None:
    manifest_path = getattr(context, "manifest_path", None)
    if manifest_path is None:
        manifest_path = Path(context.result.details["manifest_path"])
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    for artifact in manifest.get("artifacts", []):
        rel = artifact.get("path") or artifact.get("pointer")
        if not rel:
            continue
        path = Path(manifest_path).parent / rel
        if path.exists():
            path.unlink()


@then('the error should mention "missing evidence artifact"')
def step_replay_error_message(context) -> None:
    output = getattr(context, "replay_output", "")
    assert "missing evidence artifact" in output
