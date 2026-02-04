from __future__ import annotations

import hashlib
import json
from pathlib import Path

from behave import given, then

import verdict_state_steps


@given('a hypothesis library "{library_id}"')
def step_hypothesis_library(context, library_id: str) -> None:
    synthetic = verdict_state_steps._synthetic(context)
    checksum = hashlib.sha256(library_id.encode("utf-8")).hexdigest()
    synthetic.manifest_metadata = {
        "hypothesis_library_id": library_id,
        "hypothesis_library_checksum": checksum,
    }
    context.hypothesis_library_id = library_id
    context.hypothesis_checksum = checksum
    context.min_residual_mass = 0.2


@given("a run uses that library")
def step_run_uses_library(context) -> None:
    verdict_state_steps._synthetic(context)
    context.library_in_use = True


@then('the manifest should include "{field}" as "{expected}"')
def step_manifest_field(context, field: str, expected: str) -> None:
    manifest_path = context.result.details.get("manifest_path")
    assert manifest_path, "Missing manifest_path"
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    metadata = manifest.get("metadata") or {}
    assert metadata.get(field) == expected, metadata


@then("it should include a library checksum")
def step_manifest_checksum(context) -> None:
    manifest_path = context.result.details.get("manifest_path")
    assert manifest_path, "Missing manifest_path"
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    metadata = manifest.get("metadata") or {}
    checksum = metadata.get("hypothesis_library_checksum")
    assert checksum, metadata


@then('the report should include anomaly "{anomaly}"')
def step_report_anomaly(context, anomaly: str) -> None:
    anomalies = []
    if getattr(context, "decision", None):
        anomalies = context.decision.get("anomalies") or []
    if not anomalies:
        anomalies = context.result.details.get("anomalies") or []
    assert anomaly in anomalies, anomalies


@then('the credence should allocate at least "{label}" to "NOA"')
def step_residual_noa(context, label: str) -> None:
    min_value = getattr(context, label, None)
    assert min_value is not None, f"Missing {label} on context"
    ledger = (context.result.details.get("session") or {}).get("ledger") or {}
    noa_mass = ledger.get("H_NOA")
    assert noa_mass is not None, ledger
    assert noa_mass >= float(min_value), noa_mass
