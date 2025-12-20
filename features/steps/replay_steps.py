from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from behave import given, when, then

from abductio_core.application.dto import RootSpec, SessionConfig, SessionRequest
from abductio_core.application.ports import RunSessionDeps
from abductio_core.application.use_cases.run_session import run_session
from abductio_core.application.use_cases.replay_session import replay_session

from praevisio.infrastructure.abductio_ports import ListAuditSink

@dataclass
class FixedEvaluator:
    p: float

    def evaluate(self, node_key: str) -> dict:
        if ":" not in node_key:
            return {}
        return {
            "p": self.p,
            "A": 2,
            "B": 2,
            "C": 2,
            "D": 2,
            "evidence_refs": ["synthetic:evidence"],
        }


@dataclass
class FixedDecomposer:
    def decompose(self, root_id: str) -> dict:
        if ":" in root_id:
            return {}
        return {
            "ok": True,
            "feasibility_statement": "fixed",
            "availability_statement": "fixed",
            "fit_statement": "fixed",
            "defeater_statement": "fixed",
        }


@given("an evaluation with credence 0.95")
def step_eval_with_credence(context):
    evaluator = FixedEvaluator(p=0.95)
    decomposer = FixedDecomposer()
    request = SessionRequest(
        claim="synthetic claim",
        roots=[RootSpec(root_id="promise", statement="promise", exclusion_clause="none")],
        config=SessionConfig(tau=0.1, epsilon=0.05, gamma=0.2, alpha=0.4),
        credits=4,
        required_slots=[
            {"slot_key": "feasibility", "role": "NEC"},
            {"slot_key": "availability", "role": "NEC"},
            {"slot_key": "fit_to_key_features", "role": "NEC"},
            {"slot_key": "defeater_resistance", "role": "NEC"},
        ],
        run_mode="until_credits_exhausted",
    )
    audit_sink = ListAuditSink()
    result = run_session(
        request, RunSessionDeps(evaluator=evaluator, decomposer=decomposer, audit_sink=audit_sink)
    )
    context.expected_credence = 0.95
    context.result = result


@given("an audit file from that evaluation")
def step_audit_file(context):
    audit = context.result.audit
    audit_path = Path(tempfile.mkdtemp(prefix="praevisio-audit-")) / "audit.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    context.audit_path = audit_path


@when("I replay the audit")
def step_replay_audit(context):
    audit = json.loads(Path(context.audit_path).read_text(encoding="utf-8"))
    context.replay_result = replay_session(audit)


@then("the replayed credence should equal 0.95")
def step_replay_equals(context):
    ledger = context.replay_result.ledger
    actual = float(ledger.get("promise", 0.0))
    assert abs(actual - context.expected_credence) < 1e-6, actual


@given("an evaluation audit file")
def step_eval_audit_file(context):
    step_eval_with_credence(context)
    step_audit_file(context)


@when("I corrupt the audit file")
def step_corrupt_audit(context):
    Path(context.audit_path).write_text("not-json", encoding="utf-8")


@when("I try to replay it")
def step_try_replay(context):
    try:
        audit = json.loads(Path(context.audit_path).read_text(encoding="utf-8"))
        replay_session(audit)
        context.replay_error = None
    except Exception as exc:
        context.replay_error = exc


@then("the replay should fail with validation error")
def step_replay_fails(context):
    assert context.replay_error is not None, "Expected replay to fail"
