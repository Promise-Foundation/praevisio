from __future__ import annotations

from typing import Iterable, List
import os

from ..domain.models import Promise
from ..domain.ports import PromiseRepository, GitRepository, ProcessExecutor
from ..domain.config import Configuration
from ..domain.entities import HookResult, EvaluationResult
from ..domain.services import HookSelectionService
from ..domain.value_objects import ExitCode, HookType


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


def evaluate_commit(path: str) -> EvaluationResult:
    """Minimal MVP evaluation logic.

    Reads app/src/llm_client.py in the given commit directory and searches for
    a log( ... ) call. Returns a trivial credence and verdict accordingly.
    """
    file_path = os.path.join(path, "app", "src", "llm_client.py")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        return EvaluationResult(credence=0.0, verdict="red")

    has_logging = "log(" in code
    credence = 0.97 if has_logging else 0.42
    verdict = "green" if credence >= 0.95 else "red"
    return EvaluationResult(credence=credence, verdict=verdict)
