from __future__ import annotations

from typing import Iterable, List
import os

import pytest

from ..domain.models import Promise
from ..domain.ports import PromiseRepository, GitRepository, ProcessExecutor, StaticAnalyzer
from ..domain.config import Configuration
from ..domain.entities import HookResult, EvaluationResult
from ..domain.services import HookSelectionService
from ..domain.value_objects import ExitCode, HookType
from ..infrastructure.static_analysis_semgrep import SemgrepStaticAnalyzer


class PromiseService:
    """Application service for managing promises.

    Returns domain objects, keeping this layer decoupled from presentation.
    """

    def __init__(self, repository: PromiseRepository) -> None:
        self._repo = repository

    def register_promise(self, promise_id: str, statement: str) -> Promise:
        """Create and persist a new Promise.

        Parameters
        - promise_id: unique identifier for the promise
        - statement: the promise statement

        Returns
        - Promise (domain object)
        """
        promise = Promise(id=promise_id, statement=statement)
        return self._repo.save(promise)


class HookOrchestrationService:
    """Coordinates running hooks in correct order and returns results."""

    def __init__(self, git: GitRepository, executor: ProcessExecutor, selector: HookSelectionService | None = None) -> None:
        self._git = git
        self._exec = executor
        self._selector = selector or HookSelectionService()

    def run_hooks(self, hook_type: HookType, config: Configuration) -> List[HookResult]:
        context = self._build_context()
        hooks = self._selector.filter_by_type(config.hooks, hook_type)
        hooks = self._selector.sort_by_dependencies(hooks)

        results: List[HookResult] = []
        for hook in hooks:
            matched = self._selector.matched_files(hook, context)
            if hook.file_scoped and not matched:
                results.append(
                    HookResult(hook_id=hook.id, skipped=True, exit_code=ExitCode(0), matched_files=matched)
                )
                continue
            # For now we don't expand file args; just run the command.
            code = self._exec.run(hook.command)
            results.append(
                HookResult(hook_id=hook.id, skipped=False, exit_code=ExitCode(code), matched_files=matched)
            )

        return results

    def _build_context(self):
        from ..domain.entities import CommitContext

        return CommitContext(staged_files=self._git.get_staged_files(), commit_message=self._git.get_commit_message())


def evaluate_commit(
    path: str,
    analyzer: StaticAnalyzer | None = None,
) -> EvaluationResult:
    """
    Evaluate whether a commit satisfies the llm-logging-complete promise.

    Evidence sources:
    1. Pytest run of app/tests/test_logging.py (procedural evidence).
    2. SemgrepStaticAnalyzer over the given path (static_analysis evidence).

    This implementation is intentionally simple and tutorial-friendly.
    """

    analyzer = analyzer or SemgrepStaticAnalyzer()

    # --------------------
    # 1) Procedural evidence (pytest)
    # --------------------
    original_cwd = os.getcwd()
    try:
        os.chdir(path)
        # Run only the specific test file used in the tutorial
        test_result_code = pytest.main(
            ["app/tests/test_logging.py", "-q", "--disable-warnings"]
        )
    finally:
        os.chdir(original_cwd)

    test_passes = (test_result_code == 0)

    # --------------------
    # 2) Static analysis evidence (Semgrep)
    # --------------------
    sa_result = analyzer.analyze(path)
    coverage = sa_result.coverage
    total_calls = sa_result.total_llm_calls
    violations = sa_result.violations

    # --------------------
    # 3) Fuse evidence into credence
    # --------------------
    # Weighting scheme: tests 40%, Semgrep coverage 60%.
    test_contribution = 0.4 if test_passes else 0.0
    semgrep_contribution = 0.6 * coverage

    credence = test_contribution + semgrep_contribution

    # Modifier: failing tests cap credence
    if not test_passes:
        credence = min(credence, 0.70)

    # Modifier: very low coverage penalized
    if coverage < 0.85:
        credence *= 0.90

    # Modifier: if there are no LLM calls at all, treat as neutral success
    if total_calls == 0:
        credence = 0.80

    verdict = "green" if credence >= 0.95 else "red"

    details = {
        "test_passes": test_passes,
        "semgrep_coverage": coverage,
        "total_llm_calls": total_calls,
        "violations_found": violations,
        "findings": [f.__dict__ for f in sa_result.findings],
        "test_contribution": test_contribution,
        "semgrep_contribution": semgrep_contribution,
    }

    return EvaluationResult(credence=credence, verdict=verdict, details=details)
