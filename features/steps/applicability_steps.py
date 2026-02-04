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
    def analyze(self, path: str) -> StaticAnalysisResult:
        return StaticAnalysisResult(
            total_llm_calls=1,
            violations=0,
            coverage=1.0,
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


@given("a promise declares applicable as false")
def step_promise_not_applicable(context) -> None:
    context.promise = Promise(
        id="llm-input-logging",
        statement="test",
        applicable=False,
    )


@given("evaluation inputs indicate applicability")
def step_inputs_indicate_applicable(context) -> None:
    context.repo_path = Path(tempfile.mkdtemp(prefix="praevisio-applicability-"))
    context.eval_config = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.1,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
    )


@when("I run the applicability check")
def step_run_applicability_check(context) -> None:
    service = EvaluationService(
        analyzer=FixedAnalyzer(),
        test_runner=FixedTestRunner(),
        promise_loader=FixedPromiseLoader(context.promise),
    )
    context.result = service.evaluate_path(str(context.repo_path), config=context.eval_config)


@then("the evaluation should remain applicable")
def step_eval_remains_applicable(context) -> None:
    assert context.result.details.get("applicable") is True
