from __future__ import annotations

from dataclasses import dataclass
import os

from praevisio.application.evaluation_service import EvaluationService
from praevisio.domain.entities import StaticAnalysisResult
from praevisio.domain.evaluation_config import EvaluationConfig
from praevisio.domain.models import Promise


@dataclass
class FakePromiseLoader:
    promise: Promise

    def load(self, promise_id: str) -> Promise:
        return self.promise


@dataclass
class FakeAnalyzer:
    result: StaticAnalysisResult

    def analyze(self, path: str) -> StaticAnalysisResult:
        return self.result


@dataclass
class FlakyTestRunner:
    calls: int = 0

    def run(self, path: str, args: list[str]) -> int:
        if os.environ.get("PRAEVISIO_SEED"):
            return 0
        self.calls += 1
        return 0 if self.calls == 1 else 1


class FakeSessionResult:
    def __init__(self, promise_id: str) -> None:
        self.ledger = {promise_id: 1.0}
        self.roots = {promise_id: {"k_root": 1.0}}
        self.audit = {"events": []}
        self.stop_reason = "done"

    def to_dict_view(self):
        return {"ledger": self.ledger, "roots": self.roots, "stop_reason": self.stop_reason}


def _base_config() -> EvaluationConfig:
    return EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.1,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        determinism_runs=2,
    )


def _fake_run_session(session, deps):
    promise_id = session.roots[0].root_id
    return FakeSessionResult(promise_id)


def test_session_inputs_sorted(monkeypatch, tmp_path) -> None:
    captured = {}

    def capture_run_session(session, deps):
        captured["required_slots"] = session.required_slots
        captured["evidence_items"] = session.evidence_items
        return _fake_run_session(session, deps)

    monkeypatch.setattr(
        "praevisio.application.evaluation_service.run_session", capture_run_session
    )
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    runner = FlakyTestRunner()
    loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))
    service = EvaluationService(analyzer=analyzer, test_runner=runner, promise_loader=loader)
    config = _base_config()
    config = EvaluationConfig(
        promise_id=config.promise_id,
        threshold=config.threshold,
        severity=config.severity,
        pytest_args=config.pytest_args,
        pytest_targets=config.pytest_targets,
        semgrep_rules_path=config.semgrep_rules_path,
        semgrep_callsite_rule_id=config.semgrep_callsite_rule_id,
        semgrep_violation_rule_id=config.semgrep_violation_rule_id,
        thresholds=config.thresholds,
        abductio_credits=config.abductio_credits,
        abductio_tau=config.abductio_tau,
        abductio_epsilon=config.abductio_epsilon,
        abductio_gamma=config.abductio_gamma,
        abductio_gamma_noa=config.abductio_gamma_noa,
        abductio_gamma_und=config.abductio_gamma_und,
        abductio_alpha=config.abductio_alpha,
        abductio_beta=config.abductio_beta,
        abductio_weight_cap=config.abductio_weight_cap,
        abductio_lambda_voi=config.abductio_lambda_voi,
        abductio_world_mode=config.abductio_world_mode,
        abductio_required_slots=list(reversed(config.abductio_required_slots)),
        run_dir=config.run_dir,
        determinism_mode=config.determinism_mode,
        determinism_runs=config.determinism_runs,
        determinism_seed=config.determinism_seed,
    )
    service.evaluate_path(str(tmp_path), config=config)
    required_slots = captured["required_slots"]
    evidence_items = captured["evidence_items"]
    assert required_slots == sorted(
        required_slots, key=lambda slot: (slot.get("slot_key", ""), slot.get("role", ""))
    )
    assert evidence_items == sorted(
        evidence_items, key=lambda item: (item.get("id", ""), item.get("source", ""))
    )


def test_determinism_strict_blocks_on_mismatch(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("praevisio.application.evaluation_service.run_session", _fake_run_session)
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    runner = FlakyTestRunner()
    loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))
    service = EvaluationService(analyzer=analyzer, test_runner=runner, promise_loader=loader)
    config = _base_config()
    config = EvaluationConfig(
        promise_id=config.promise_id,
        threshold=config.threshold,
        severity=config.severity,
        pytest_args=config.pytest_args,
        pytest_targets=config.pytest_targets,
        semgrep_rules_path=config.semgrep_rules_path,
        semgrep_callsite_rule_id=config.semgrep_callsite_rule_id,
        semgrep_violation_rule_id=config.semgrep_violation_rule_id,
        thresholds=config.thresholds,
        abductio_credits=config.abductio_credits,
        abductio_tau=config.abductio_tau,
        abductio_epsilon=config.abductio_epsilon,
        abductio_gamma=config.abductio_gamma,
        abductio_gamma_noa=config.abductio_gamma_noa,
        abductio_gamma_und=config.abductio_gamma_und,
        abductio_alpha=config.abductio_alpha,
        abductio_beta=config.abductio_beta,
        abductio_weight_cap=config.abductio_weight_cap,
        abductio_lambda_voi=config.abductio_lambda_voi,
        abductio_world_mode=config.abductio_world_mode,
        abductio_required_slots=config.abductio_required_slots,
        run_dir=config.run_dir,
        determinism_mode="strict",
        determinism_runs=2,
        determinism_seed=None,
    )
    result = service.evaluate_path(str(tmp_path), config=config)
    assert result.verdict == "error"
    assert result.details["determinism"]["mismatch"] is True
    assert "toolchain_nondeterminism" in result.details["anomalies"]


def test_determinism_seed_stabilizes(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("praevisio.application.evaluation_service.run_session", _fake_run_session)
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    runner = FlakyTestRunner()
    loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))
    service = EvaluationService(analyzer=analyzer, test_runner=runner, promise_loader=loader)
    config = _base_config()
    config = EvaluationConfig(
        promise_id=config.promise_id,
        threshold=config.threshold,
        severity=config.severity,
        pytest_args=config.pytest_args,
        pytest_targets=config.pytest_targets,
        semgrep_rules_path=config.semgrep_rules_path,
        semgrep_callsite_rule_id=config.semgrep_callsite_rule_id,
        semgrep_violation_rule_id=config.semgrep_violation_rule_id,
        thresholds=config.thresholds,
        abductio_credits=config.abductio_credits,
        abductio_tau=config.abductio_tau,
        abductio_epsilon=config.abductio_epsilon,
        abductio_gamma=config.abductio_gamma,
        abductio_gamma_noa=config.abductio_gamma_noa,
        abductio_gamma_und=config.abductio_gamma_und,
        abductio_alpha=config.abductio_alpha,
        abductio_beta=config.abductio_beta,
        abductio_weight_cap=config.abductio_weight_cap,
        abductio_lambda_voi=config.abductio_lambda_voi,
        abductio_world_mode=config.abductio_world_mode,
        abductio_required_slots=config.abductio_required_slots,
        run_dir=config.run_dir,
        determinism_mode="warn",
        determinism_runs=2,
        determinism_seed=123,
    )
    result = service.evaluate_path(str(tmp_path), config=config)
    assert result.verdict != "error"
    assert result.details["determinism"]["mismatch"] is False


def test_applicability_override_ignored(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("praevisio.application.evaluation_service.run_session", _fake_run_session)
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    runner = FlakyTestRunner()
    loader = FakePromiseLoader(
        Promise(id="llm-input-logging", statement="test", applicable=False)
    )
    service = EvaluationService(analyzer=analyzer, test_runner=runner, promise_loader=loader)
    config = _base_config()
    result = service.evaluate_path(str(tmp_path), config=config)
    assert result.details["applicable"] is True
    assert "applicability_override_ignored" in result.details["anomalies"]
