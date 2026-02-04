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
from praevisio.domain.models import Promise


PROMISE_ID = "llm-input-logging"


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


def _write_config(repo_path: Path, *, severity: str | None = None) -> Path:
    lines = [
        "evaluation:",
        f"  promise_id: {PROMISE_ID}",
        "  threshold: 0.80",
        "  abductio_credits: 8",
        "  pytest_targets:",
        "    - tests/test_logging.py",
        "  semgrep_rules_path: rules.yaml",
        "  thresholds:",
        "    low: 0.60",
        "    medium: 0.80",
        "    high: 0.95",
        "  run_dir: .praevisio/runs",
    ]
    if severity:
        lines.insert(2, f"  severity: {severity}")
    lines.append("hooks: []")
    config_path = repo_path / ".praevisio.yaml"
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


def _patch_service(context) -> None:
    service = EvaluationService(
        analyzer=context.analyzer,
        test_runner=context.test_runner,
        promise_loader=context.promise_loader,
    )
    context._original_build_service = getattr(cli_module, "build_evaluation_service", None)
    cli_module.build_evaluation_service = lambda: service


def _restore_service(context) -> None:
    if getattr(context, "_original_build_service", None) is not None:
        cli_module.build_evaluation_service = context._original_build_service


def _latest_run_dir(context) -> Path:
    runs_dir = Path(context.repo_path) / context.runs_dir
    candidates = [p for p in runs_dir.iterdir() if p.is_dir()]
    assert candidates, f"No runs under {runs_dir}"
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _run_evaluate_commit(context) -> None:
    _patch_service(context)
    args = [
        "evaluate-commit",
        str(context.repo_path),
        "--config",
        str(context.config_path),
        "--json",
    ]
    result = context.runner.invoke(cli_module.app, args)
    context.cli_result = result
    context.last_output = result.output
    _restore_service(context)


def _ensure_decision_loaded(context) -> None:
    if getattr(context, "decision", None) is not None:
        return
    latest = _latest_run_dir(context)
    decision_path = latest / "decision.json"
    context.decision = json.loads(decision_path.read_text(encoding="utf-8"))


@given("a Praevisio configuration with severity thresholds")
def step_config_with_thresholds(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-verdict-"))
    context.repo_path = repo_dir
    context.runner = CliRunner()
    context.analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    context.test_runner = FakeTestRunner(exit_code=0)
    context.promise_loader = FakePromiseLoader(
        Promise(id=PROMISE_ID, statement="test")
    )
    context.config_path = _write_config(repo_dir, severity=None)


@given('the evaluation is for a promise with severity "high"')
def step_set_severity_high(context) -> None:
    context.config_path = _write_config(context.repo_path, severity="high")


@given('the run artifacts directory is ".praevisio/runs"')
def step_set_runs_dir(context) -> None:
    context.runs_dir = ".praevisio/runs"


@when('I run "praevisio ci-gate . --fail-on-violation --config .praevisio.yaml"')
def step_run_ci_gate(context) -> None:
    _patch_service(context)
    args = [
        "ci-gate",
        str(context.repo_path),
        "--fail-on-violation",
        "--config",
        str(context.config_path),
    ]
    result = context.runner.invoke(cli_module.app, args)
    context.cli_result = result
    context.last_output = result.output
    _restore_service(context)


@then('the latest run directory should contain "manifest.json"')
def step_latest_run_manifest(context) -> None:
    context.latest_run_dir = _latest_run_dir(context)
    assert (context.latest_run_dir / "manifest.json").exists()


@then('it should contain "audit.json"')
def step_latest_run_audit(context) -> None:
    if not getattr(context, "latest_run_dir", None):
        context.latest_run_dir = _latest_run_dir(context)
    assert (context.latest_run_dir / "audit.json").exists()


@then('it should contain "decision.json"')
def step_latest_run_decision(context) -> None:
    if not getattr(context, "latest_run_dir", None):
        context.latest_run_dir = _latest_run_dir(context)
    decision_path = context.latest_run_dir / "decision.json"
    assert decision_path.exists()
    context.decision = json.loads(decision_path.read_text(encoding="utf-8"))


@then('"decision.json" should include "schema_version"')
def step_decision_schema(context) -> None:
    assert "schema_version" in context.decision


@then('it should include "run_id"')
def step_decision_run_id(context) -> None:
    assert context.decision.get("run_id")


@then('it should include "timestamp_utc"')
def step_decision_timestamp(context) -> None:
    assert context.decision.get("timestamp_utc")


@then('it should include "policy" describing thresholds and enforcement rules')
def step_decision_policy(context) -> None:
    policy = context.decision.get("policy")
    assert isinstance(policy, dict)
    assert "thresholds" in policy
    assert "enforcement" in policy


@then('it should include an "overall_verdict"')
def step_decision_overall(context) -> None:
    if getattr(context, "decision", None):
        assert context.decision.get("overall_verdict") is not None
        return
    report_path = getattr(context, "report_path", None)
    if report_path:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
        assert "overall_verdict" in report, report
        return
    raise AssertionError("No decision or report available for overall_verdict check")


@then('it should include a list "promise_results"')
def step_decision_promise_results(context) -> None:
    results = context.decision.get("promise_results")
    assert isinstance(results, list) and results


@then('each promise result should include "promise_id", "threshold", "credence", and "verdict"')
def step_promise_fields(context) -> None:
    for item in context.decision.get("promise_results", []):
        assert "promise_id" in item
        assert "threshold" in item
        assert "credence" in item
        assert "verdict" in item


@then('"decision.json" should reference "audit_sha256" and "manifest_sha256"')
def step_decision_hashes(context) -> None:
    assert context.decision.get("audit_sha256")
    assert context.decision.get("manifest_sha256")


@then('"decision.json" should include "notification"')
def step_decision_notification(context) -> None:
    _ensure_decision_loaded(context)
    assert "notification" in context.decision


@then('"notification" should include "action" as "change_blocked" or "change_allowed"')
def step_notification_action(context) -> None:
    _ensure_decision_loaded(context)
    action = context.decision["notification"].get("action")
    assert action in {"change_blocked", "change_allowed"}


@then('"notification" should include "impact" as one of "low|medium|high|critical"')
def step_notification_impact(context) -> None:
    _ensure_decision_loaded(context)
    impact = context.decision["notification"].get("impact")
    assert impact in {"low", "medium", "high", "critical"}


@then('"notification" should include "likelihood" as one of "unlikely|possible|likely|near_certain"')
def step_notification_likelihood(context) -> None:
    _ensure_decision_loaded(context)
    likelihood = context.decision["notification"].get("likelihood")
    assert likelihood in {"unlikely", "possible", "likely", "near_certain"}


@then('"notification" should include "confidence" as one of "low|medium|high"')
def step_notification_confidence(context) -> None:
    _ensure_decision_loaded(context)
    confidence = context.decision["notification"].get("confidence")
    assert confidence in {"low", "medium", "high"}


@then('the notification payload should include a human-readable "summary"')
def step_notification_summary(context) -> None:
    _ensure_decision_loaded(context)
    summary = context.decision["notification"].get("summary")
    assert isinstance(summary, str) and summary.strip()


@given('I have the latest run\'s "audit.json"')
def step_have_latest_audit(context) -> None:
    runs_dir = Path(context.repo_path) / context.runs_dir
    if not runs_dir.exists() or not list(runs_dir.iterdir()):
        _run_evaluate_commit(context)
    context.latest_run_dir = _latest_run_dir(context)
    context.audit_path = context.latest_run_dir / "audit.json"
    context.decision = json.loads(
        (context.latest_run_dir / "decision.json").read_text(encoding="utf-8")
    )


@when('I run "praevisio replay-audit --latest --json"')
def step_run_replay_latest(context) -> None:
    args = [
        "replay-audit",
        "--latest",
        "--runs-dir",
        str(Path(context.repo_path) / context.runs_dir),
        "--json",
    ]
    result = context.runner.invoke(cli_module.app, args)
    context.replay_result = result
    context.replay_payload = json.loads(result.output)


@then("the replayed ledger should reproduce the same credence values used in \"decision.json\"")
def step_replay_credence_matches(context) -> None:
    ledger = context.replay_payload.get("ledger", {})
    for item in context.decision.get("promise_results", []):
        promise_id = item.get("promise_id")
        expected = float(item.get("credence"))
        actual = float(ledger.get(promise_id, 0.0))
        assert abs(actual - expected) < 1e-6, (promise_id, actual, expected)


@then('the recomputed "overall_verdict" should match "decision.json"')
def step_recompute_overall(context) -> None:
    policy = context.decision.get("policy") or {}
    tau = float(policy.get("tau", 0.0))
    ledger = context.replay_payload.get("ledger", {})
    roots = context.replay_payload.get("roots", {}) or {}
    verdicts = []
    for item in context.decision.get("promise_results", []):
        promise_id = item.get("promise_id")
        threshold = float(item.get("threshold", 0.0))
        credence = float(ledger.get(promise_id, 0.0))
        k_root = float((roots.get(promise_id) or {}).get("k_root", 0.0))
        verdicts.append("green" if credence >= threshold and k_root >= tau else "red")
    overall = "red" if "red" in verdicts else "green"
    assert overall == context.decision.get("overall_verdict")
