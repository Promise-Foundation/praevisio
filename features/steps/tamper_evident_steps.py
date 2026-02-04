from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from behave import given, when, then
from typer.testing import CliRunner

import praevisio.presentation.cli as cli_module
from praevisio.application.evaluation_service import EvaluationService
from praevisio.domain.entities import StaticAnalysisResult
from praevisio.domain.evaluation_config import EvaluationConfig
from praevisio.domain.models import Promise
from praevisio.infrastructure.audit_chain import validate_audit_log
from praevisio.infrastructure.report_signing import verify_bytes
from abductio_core.application.use_cases.replay_session import replay_session


@dataclass
class FakeAnalyzer:
    result: StaticAnalysisResult

    def analyze(self, path: str) -> StaticAnalysisResult:
        return self.result


@dataclass
class FakeTestRunner:
    exit_code: int = 0

    def run(self, path: str, args: list[str]) -> int:
        return self.exit_code


@dataclass
class FakePromiseLoader:
    promise: Promise

    def load(self, promise_id: str) -> Promise:
        return self.promise


def _extract_events(audit: object) -> list[dict]:
    if isinstance(audit, dict) and isinstance(audit.get("events"), list):
        return audit["events"]
    if isinstance(audit, list):
        return audit
    return []


@given("an evaluation run completed with an audit log")
def step_eval_completed(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-audit-chain-"))
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    runner = FakeTestRunner(exit_code=0)
    loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))
    service = EvaluationService(analyzer=analyzer, test_runner=runner, promise_loader=loader)
    config = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.1,
        pytest_targets=[],
        semgrep_rules_path="rules.yaml",
        run_dir=".praevisio/runs",
    )
    result = service.evaluate_path(str(repo_dir), config=config)
    context.result = result
    details = result.details
    context.audit_path = Path(details["audit_path"])
    context.report_path = Path(details["report_path"])
    context.report_sig_path = Path(details["report_signature_path"])


@given("audit log chaining is enabled")
def step_chaining_enabled(context) -> None:
    pass


@given("report signing is enabled")
def step_signing_enabled(context) -> None:
    pass


@when("I inspect the audit log entries")
def step_inspect_audit_entries(context) -> None:
    audit = json.loads(Path(context.audit_path).read_text(encoding="utf-8"))
    context.audit_entries = _extract_events(audit)


@then('each entry should include "entry_hash"')
def step_entry_hash_present(context) -> None:
    for entry in context.audit_entries:
        payload = entry.get("payload") or {}
        assert "entry_hash" in payload, entry


@then('each entry should include "prev_hash"')
def step_prev_hash_present(context) -> None:
    for entry in context.audit_entries:
        payload = entry.get("payload") or {}
        assert "prev_hash" in payload, entry


@then('the first entry should include "prev_hash" set to "GENESIS"')
def step_genesis_prev_hash(context) -> None:
    first = context.audit_entries[0]
    payload = first.get("payload") or {}
    assert payload.get("prev_hash") == "GENESIS", payload


@given("an audit file from the evaluation")
def step_audit_file_from_eval(context) -> None:
    assert context.audit_path.exists(), context.audit_path


@when("I reorder two audit log entries")
def step_reorder_entries(context) -> None:
    audit = json.loads(Path(context.audit_path).read_text(encoding="utf-8"))
    entries = _extract_events(audit)
    if len(entries) >= 2:
        entries[0], entries[1] = entries[1], entries[0]
    Path(context.audit_path).write_text(json.dumps(audit, indent=2), encoding="utf-8")


@when("I remove one audit log entry")
def step_remove_entry(context) -> None:
    audit = json.loads(Path(context.audit_path).read_text(encoding="utf-8"))
    entries = _extract_events(audit)
    if len(entries) > 1:
        entries.pop(1)
    elif entries:
        entries.pop()
    Path(context.audit_path).write_text(json.dumps(audit, indent=2), encoding="utf-8")


@when("I try to replay the audit")
def step_try_replay_audit(context) -> None:
    if getattr(context, "use_cli_replay", False):
        runner = CliRunner()
        result = runner.invoke(cli_module.app, ["replay-audit", str(context.audit_path)])
        context.replay_output = result.output
        if result.exit_code != 0:
            context.replay_error = RuntimeError(result.output)
            context.error = context.replay_error
        else:
            context.replay_error = None
        return
    audit = json.loads(Path(context.audit_path).read_text(encoding="utf-8"))
    ok, error = validate_audit_log(audit)
    if not ok:
        context.replay_error = RuntimeError(error)
        context.error = context.replay_error
        return
    try:
        replay_session(audit)
        context.replay_error = None
    except Exception as exc:
        context.replay_error = exc
        context.error = exc


@given("a signed evaluation report")
def step_signed_report(context) -> None:
    assert context.report_path.exists(), context.report_path
    assert context.report_sig_path.exists(), context.report_sig_path


@when("I verify the report signature")
def step_verify_report_signature(context) -> None:
    report_bytes = Path(context.report_path).read_bytes()
    signature = Path(context.report_sig_path).read_text(encoding="utf-8")
    if verify_bytes(report_bytes, signature):
        context.signature_valid = True
        context.signature_error = None
    else:
        context.signature_valid = False
        context.signature_error = RuntimeError("signature verification failed")
        context.error = context.signature_error


@then("verification should succeed")
def step_verification_succeeds(context) -> None:
    assert context.signature_valid is True


@when("I modify the report content")
def step_modify_report(context) -> None:
    path = Path(context.report_path)
    content = path.read_text(encoding="utf-8")
    path.write_text(content + "\n", encoding="utf-8")


@then("verification should fail")
def step_verification_fails(context) -> None:
    assert context.signature_valid is False
