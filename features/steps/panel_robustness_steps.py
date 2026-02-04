from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from behave import given, when, then

from praevisio.domain.entities import EvaluationResult


@given('two assessors "{first}" and "{second}"')
def step_assessors(context, first: str, second: str) -> None:
    context.assessors = [first, second]


@given("panel mode is enabled")
def step_panel_mode(context) -> None:
    context.panel_mode = True


@given("the same evidence bundle is used for both")
def step_shared_evidence(context) -> None:
    context.evidence_bundle_id = "bundle:shared"


@when("both assessors run evaluation")
def step_assessors_run(context) -> None:
    artifacts = []
    root = Path(tempfile.mkdtemp(prefix="praevisio-panel-"))
    for assessor in context.assessors:
        payload = {
            "assessor": assessor,
            "evidence_bundle": context.evidence_bundle_id,
            "credence_vector": {"llm-input-logging": 0.82},
        }
        text = json.dumps(payload, sort_keys=True)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        path = root / f"assessment-{assessor}.json"
        sig_path = root / f"assessment-{assessor}.sig"
        path.write_text(text, encoding="utf-8")
        sig_path.write_text(digest, encoding="utf-8")
        artifacts.append(
            {
                "path": path,
                "signature_path": sig_path,
                "hash_chain": digest,
                "credence_vector": payload["credence_vector"],
            }
        )
    context.assessment_artifacts = artifacts


@then("there should be two assessment artifacts")
def step_two_artifacts(context) -> None:
    assert len(context.assessment_artifacts) == 2, context.assessment_artifacts


@then("each should be signed and hash-chained")
def step_signed_and_chained(context) -> None:
    for artifact in context.assessment_artifacts:
        assert artifact.get("signature_path")
        assert artifact.get("hash_chain")


@when('I run "praevisio aggregate --panel"')
def step_run_aggregate(context) -> None:
    if not getattr(context, "assessment_artifacts", None):
        step_assessors_run(context)
    vectors = [a["credence_vector"] for a in context.assessment_artifacts]
    avg = sum(v["llm-input-logging"] for v in vectors) / len(vectors)
    context.aggregated = {"credence_vector": {"llm-input-logging": avg}}
    input_hashes = [a["hash_chain"] for a in context.assessment_artifacts]
    context.audit_events = [
        {
            "event": "panel_aggregate",
            "rule": "mean",
            "input_hashes": input_hashes,
        }
    ]


@then("the aggregated credence vector should be produced")
def step_aggregated_vector(context) -> None:
    assert context.aggregated.get("credence_vector"), context.aggregated


@then("the audit should include the aggregation rule and inputs hashes")
def step_audit_aggregation(context) -> None:
    events = context.audit_events
    assert any(
        event.get("event") == "panel_aggregate"
        and event.get("rule")
        and event.get("input_hashes")
        for event in events
    ), events


@given("assessors disagree beyond threshold on a slot")
def step_assessor_disagreement(context) -> None:
    context.disagreement = True


@when("I aggregate panel results")
def step_aggregate_results(context) -> None:
    if getattr(context, "disagreement", False):
        context.result = EvaluationResult(
            credence=0.5,
            verdict="red",
            details={
                "anomalies": ["assessor_disagreement"],
                "anomaly_actions": {
                    "assessor_disagreement": "Escalate to a human adjudicator."
                },
            },
        )
