from __future__ import annotations

from pathlib import Path

from ..domain.entities import EvaluationResult
from ..domain.evaluation_config import EvaluationConfig
from ..domain.ports import StaticAnalyzer, TestRunner
from ..infrastructure.static_analysis_semgrep import SemgrepStaticAnalyzer
from ..infrastructure.test_runner_subprocess import SubprocessPytestRunner


class EvaluationService:
    """Evaluate a commit against built-in tutorial evidence sources."""

    def __init__(
        self,
        analyzer: StaticAnalyzer | None = None,
        test_runner: TestRunner | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._test_runner = test_runner or SubprocessPytestRunner()

    def evaluate_path(self, path: str, config: EvaluationConfig | None = None) -> EvaluationResult:
        """
        Evaluate whether a commit satisfies the llm-logging-complete promise.

        Evidence sources:
        1. Pytest run of app/tests/test_logging.py (procedural evidence).
        2. SemgrepStaticAnalyzer over the given path (static_analysis evidence).
        """
        evaluation = config or EvaluationConfig()
        analyzer = self._analyzer or SemgrepStaticAnalyzer(
            rules_path=Path(evaluation.semgrep_rules_path)
        )

        test_passes = None
        test_result_code = None
        if evaluation.pytest_targets:
            test_result_code = self._test_runner.run(
                path, [*evaluation.pytest_targets, *evaluation.pytest_args]
            )
            test_passes = (test_result_code == 0)

        sa_result = analyzer.analyze(path)
        coverage = sa_result.coverage
        total_calls = sa_result.total_llm_calls
        violations = sa_result.violations

        # Weighting scheme: tests 40%, Semgrep coverage 60%.
        test_contribution = 0.4 if test_passes else 0.0
        semgrep_contribution = 0.6 * coverage

        credence = test_contribution + semgrep_contribution

        # Modifier: failing tests cap credence
        if test_passes is False:
            credence = min(credence, 0.70)

        # Modifier: very low coverage penalized
        if coverage < 0.85:
            credence *= 0.90

        if total_calls == 0:
            credence = None
            verdict = "n/a"
        else:
            verdict = "green" if credence >= evaluation.threshold else "red"

        details = {
            "test_passes": test_passes,
            "tests_skipped": test_passes is None,
            "semgrep_coverage": coverage,
            "total_llm_calls": total_calls,
            "violations_found": violations,
            "findings": [f.__dict__ for f in sa_result.findings],
            "test_contribution": test_contribution,
            "semgrep_contribution": semgrep_contribution,
            "applicable": total_calls > 0,
            "promise_id": evaluation.promise_id,
            "threshold": evaluation.threshold,
        }

        return EvaluationResult(credence=credence, verdict=verdict, details=details)
