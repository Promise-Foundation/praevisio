from __future__ import annotations

from typing import Iterable, List

from ..domain.models import Promise
from ..domain.ports import PromiseRepository, GitRepository, ProcessExecutor
from ..domain.config import Configuration
from ..domain.entities import HookResult
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
