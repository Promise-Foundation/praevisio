from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from praevisio.application.evaluation_service import EvaluationService
from praevisio.domain.entities import StaticAnalysisResult
from praevisio.domain.evaluation_config import EvaluationConfig


@dataclass
class FakeTestRunner:
    exit_code: int = 0

    def run(self, path: str, args: list[str]) -> int:
        return self.exit_code


@dataclass
class FakeAnalyzer:
    result: StaticAnalysisResult

    def analyze(self, path: str) -> StaticAnalysisResult:
        return self.result


def _base_config() -> EvaluationConfig:
    return EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.2,
        abductio_tau=0.1,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        run_dir=".praevisio/runs",
    )


def test_abductio_happy_path(tmp_path: Path) -> None:
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=10, violations=0, coverage=0.98, findings=[])
    )
    runner = FakeTestRunner(exit_code=0)
    service = EvaluationService(analyzer=analyzer, test_runner=runner)
    result = service.evaluate_path(str(tmp_path), config=_base_config())

    assert result.verdict == "green"
    assert result.details.get("audit_path")
    assert result.details.get("manifest_path")
    refs = result.details.get("evidence_refs", {})
    assert refs.get("pytest")
    assert refs.get("semgrep")

    manifest_path = Path(result.details["manifest_path"])
    assert manifest_path.exists()


def test_abductio_defeater_red(tmp_path: Path) -> None:
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=10, violations=2, coverage=0.98, findings=[])
    )
    runner = FakeTestRunner(exit_code=0)
    service = EvaluationService(analyzer=analyzer, test_runner=runner)
    config = _base_config()
    config = EvaluationConfig(
        promise_id=config.promise_id,
        threshold=0.9,
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
        abductio_alpha=config.abductio_alpha,
        abductio_required_slots=config.abductio_required_slots,
        run_dir=config.run_dir,
    )
    result = service.evaluate_path(str(tmp_path), config=config)

    assert result.verdict == "red"
    assert result.details.get("audit_path")
    assert result.details.get("manifest_path")


def test_abductio_semgrep_misconfig_is_error(tmp_path: Path) -> None:
    runner = FakeTestRunner(exit_code=0)
    service = EvaluationService(analyzer=None, test_runner=runner)
    config = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.5,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        semgrep_callsite_rule_id="",
        semgrep_violation_rule_id="",
        run_dir=".praevisio/runs",
    )
    result = service.evaluate_path(str(tmp_path), config=config)

    assert result.verdict == "error"
    assert result.details.get("manifest_path")
