from __future__ import annotations

import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory

from behave import given, when, then
from typer.testing import CliRunner

import praevisio.presentation.cli as cli_module
from praevisio.domain.entities import EvaluationResult


def _cleanup_tmpdir(context) -> None:
    if getattr(context, "_tmpdir_cleaned", False):
        return
    if getattr(context, "original_cwd", None):
        os.chdir(context.original_cwd)
    if getattr(context, "tmpdir", None):
        context.tmpdir.cleanup()
    context._tmpdir_cleaned = True


def _safe_getcwd() -> str:
    try:
        return os.getcwd()
    except FileNotFoundError:
        repo_root = Path(__file__).resolve().parents[2]
        os.chdir(repo_root)
        return os.getcwd()


@given("a git working directory with no existing pre-commit hook")
def step_git_workdir_without_hook(context) -> None:
    """Set up a temporary git repository without a pre-commit hook."""
    context._tmpdir_cleaned = False
    context.tmpdir = TemporaryDirectory()
    context.original_cwd = _safe_getcwd()
    os.chdir(context.tmpdir.name)

    git_hooks = Path(".git/hooks")
    git_hooks.mkdir(parents=True, exist_ok=True)

    precommit = git_hooks / "pre-commit"
    if precommit.exists():
        precommit.unlink()

    context.git_hooks_dir = git_hooks
    context.precommit_path = precommit
    context.runner = CliRunner()
    config_path = Path(".praevisio.yaml")
    config_path.write_text(
        "\n".join([
            "evaluation:",
            "  promise_id: llm-input-logging",
            "  threshold: 0.95",
            "  pytest_targets: []",
            "  semgrep_rules_path: governance/evidence/semgrep_rules.yaml",
            "hooks: []",
            "",
        ]),
        encoding="utf-8",
    )


@given('a critical logging promise "{promise_id}" with threshold 0.95')
def step_critical_promise(context, promise_id: str) -> None:
    context.promise_id = promise_id
    context.threshold = 0.95
    context.critical = True


@when('I run "praevisio install-hooks"')
def step_run_install_hooks(context) -> None:
    result = context.runner.invoke(cli_module.app, ["install-hooks"])
    context.install_result = result


@then("a git pre-commit hook should be installed")
def step_precommit_hook_installed(context) -> None:
    pre = context.precommit_path
    assert pre.exists(), f"Expected {pre} to exist after install-hooks"
    mode = pre.stat().st_mode
    assert mode & stat.S_IXUSR, "pre-commit hook is not executable for user"


@then('the pre-commit hook should invoke "praevisio pre-commit"')
def step_precommit_hook_invokes_praevisio(context) -> None:
    content = context.precommit_path.read_text(encoding="utf-8")
    assert "praevisio pre-commit" in content, (
        f"Expected pre-commit hook to call 'praevisio pre-commit', "
        f"but got:\n{content}"
    )
    _cleanup_tmpdir(context)


@given("the evaluation credence for critical promises will be {credence:f}")
def step_mock_critical_evaluation(context, credence: float) -> None:
    context.mock_credence = credence

    class FakeEvaluationService:
        def evaluate_path(self, path: str, *args, **kwargs) -> EvaluationResult:
            config = kwargs.get("config")
            threshold = getattr(config, "threshold", context.threshold)
            verdict = "green" if credence >= threshold else "red"
            return EvaluationResult(
                credence=credence,
                verdict=verdict,
                details={
                    "is_critical": context.critical,
                    "threshold": threshold,
                    "test_passes": credence >= threshold,
                    "semgrep_coverage": 1.0,
                },
            )

    context._original_build_service = getattr(cli_module, "build_evaluation_service", None)
    cli_module.build_evaluation_service = lambda: FakeEvaluationService()


@when('I run "praevisio pre-commit"')
def step_run_precommit(context) -> None:
    result = context.runner.invoke(cli_module.app, ["pre-commit"])
    context.precommit_result = result

    if getattr(context, "_original_build_service", None) is not None:
        cli_module.build_evaluation_service = context._original_build_service

    _cleanup_tmpdir(context)


@then("the pre-commit gate should pass")
def step_precommit_gate_pass(context) -> None:
    r = context.precommit_result
    assert r.exit_code == 0, (
        f"Expected pre-commit to pass (exit 0), "
        f"got {r.exit_code}.\nOutput:\n{r.output}"
    )


@then("the pre-commit gate should fail")
def step_precommit_gate_fail(context) -> None:
    r = context.precommit_result
    assert r.exit_code != 0, (
        f"Expected pre-commit to fail (non-zero exit), "
        f"got {r.exit_code}.\nOutput:\n{r.output}"
    )
