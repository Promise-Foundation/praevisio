from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from behave import given, when, then

from praevisio.application.evaluation_service import EvaluationService
from praevisio.domain.entities import StaticAnalysisResult
from praevisio.domain.evaluation_config import EvaluationConfig
from praevisio.domain.models import Promise


@dataclass
class FixedAnalyzer:
    coverage: float = 1.0

    def analyze(self, path: str) -> StaticAnalysisResult:
        return StaticAnalysisResult(
            total_llm_calls=1,
            violations=0,
            coverage=self.coverage,
            findings=[],
        )


@dataclass
class FixedTestRunner:
    exit_code: int = 0

    def run(self, path: str, args: list[str]) -> int:
        return self.exit_code


@dataclass
class FixedPromiseLoader:
    promise: Promise

    def load(self, promise_id: str) -> Promise:
        return self.promise


@given("a deterministic evaluation with shuffled required slots")
def step_setup_permutation_eval(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-permutation-"))
    context.repo_path = repo_dir
    context.analyzer = FixedAnalyzer()
    context.test_runner = FixedTestRunner()
    context.promise_loader = FixedPromiseLoader(Promise(id="llm-input-logging", statement="test"))

    base_slots = [
        {"slot_key": "feasibility", "role": "NEC"},
        {"slot_key": "availability", "role": "NEC"},
        {"slot_key": "fit_to_key_features", "role": "NEC"},
        {"slot_key": "defeater_resistance", "role": "NEC"},
    ]
    shuffled = [base_slots[2], base_slots[0], base_slots[3], base_slots[1]]
    reversed_slots = list(reversed(shuffled))

    context.config_a = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.1,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        determinism_runs=1,
        abductio_required_slots=shuffled,
    )
    context.config_b = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.1,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        determinism_runs=1,
        abductio_required_slots=reversed_slots,
    )


@when("I run the evaluation twice with slot permutations")
def step_run_permutation_eval(context) -> None:
    service = EvaluationService(
        analyzer=context.analyzer,
        test_runner=context.test_runner,
        promise_loader=context.promise_loader,
    )
    context.result_a = service.evaluate_path(str(context.repo_path), config=context.config_a)
    context.result_b = service.evaluate_path(str(context.repo_path), config=context.config_b)


@then("the results should be permutation invariant")
def step_assert_permutation_invariance(context) -> None:
    result_a = context.result_a
    result_b = context.result_b
    assert result_a.credence == result_b.credence
    assert result_a.verdict == result_b.verdict
    assert result_a.details.get("anomalies") == result_b.details.get("anomalies")

    session_a = (result_a.details.get("session") or {})
    session_b = (result_b.details.get("session") or {})
    assert session_a.get("ledger") == session_b.get("ledger")
    assert session_a.get("roots") == session_b.get("roots")
