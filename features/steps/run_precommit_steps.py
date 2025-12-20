from __future__ import annotations

from behave import given, when, then

from praevisio.application.hook_service import HookOrchestrationService
from praevisio.domain.config import Configuration
from praevisio.domain.entities import Hook
from praevisio.domain.services import HookSelectionService
from praevisio.domain.value_objects import FilePattern, HookType
from praevisio.infrastructure.git import InMemoryGitRepository
from praevisio.infrastructure.process import RecordingProcessExecutor


@given("a repository with staged Python files")
def step_repo_with_python(context):
    context.git = InMemoryGitRepository(staged_files=["app/main.py", "utils/helpers.py"])


@given('a hook configuration for pattern "{pattern}"')
def step_hook_config(context, pattern: str):
    hook = Hook(
        id="test-js-hook",
        name="Test JS Hook",
        type=HookType.PRE_COMMIT,
        command=["echo", "js-lint"],
        patterns=[FilePattern(pattern)],
    )
    context.configuration = Configuration(hooks=[hook])


@when("I run pre-commit hooks")
def step_run_precommit(context):
    executor = RecordingProcessExecutor()
    service = HookOrchestrationService(context.git, executor, HookSelectionService())
    context.results = service.run_hooks(HookType.PRE_COMMIT, context.configuration)
    context.executor = executor


@then("the hook should be skipped")
def step_hook_skipped(context):
    assert len(context.results) == 1
    res = context.results[0]
    assert res.skipped is True
    assert len(context.executor.commands) == 0  # ensure nothing ran
