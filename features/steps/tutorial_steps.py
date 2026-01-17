from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from behave import given, when, then
from typer.testing import CliRunner

import praevisio.presentation.cli as cli_module
from praevisio.application.evaluation_service import EvaluationService
from praevisio.domain.entities import StaticAnalysisResult
from praevisio.domain.models import Promise


@dataclass
class FakeAnalyzer:
    result: StaticAnalysisResult

    def analyze(self, path: str) -> StaticAnalysisResult:
        return self.result


@dataclass
class FakePromiseLoader:
    promise: Promise

    def load(self, promise_id: str) -> Promise:
        return self.promise


def _write_test_file(repo_path: Path, passes: bool) -> None:
    tests_dir = repo_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    body = "def test_smoke():\n"
    if passes:
        body += "    assert True\n"
    else:
        body += "    assert False\n"
    (tests_dir / "test_logging.py").write_text(body, encoding="utf-8")


def _write_config(repo_path: Path) -> Path:
    config_path = repo_path / ".praevisio.yaml"
    config_path.write_text(
        "\n".join(
            [
                "evaluation:",
                "  promise_id: llm-input-logging",
                "  threshold: 0.90",
                "  abductio_credits: 8",
                "  pytest_targets:",
                "    - tests/test_logging.py",
                "  semgrep_rules_path: governance/evidence/semgrep_rules.yaml",
                "hooks: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


@given("a tutorial repo with passing tests")
def step_repo_with_passing_tests(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-tutorial-"))
    _write_test_file(repo_dir, passes=True)
    context.repo_path = repo_dir
    context.config_path = _write_config(repo_dir)
    context.runner = CliRunner()


@given("a tutorial repo with failing tests")
def step_repo_with_failing_tests(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-tutorial-"))
    _write_test_file(repo_dir, passes=False)
    context.repo_path = repo_dir
    context.config_path = _write_config(repo_dir)
    context.runner = CliRunner()


@given("the evaluation service uses a fake analyzer")
def step_fake_analyzer(context) -> None:
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))
    service = EvaluationService(analyzer=analyzer, promise_loader=loader)
    context._original_build_service = getattr(cli_module, "build_evaluation_service", None)
    cli_module.build_evaluation_service = lambda: service


@when("I run the tutorial evaluation")
def step_run_tutorial_evaluation(context) -> None:
    args = [
        "evaluate-commit",
        str(context.repo_path),
        "--json",
        "--config",
        str(context.config_path),
    ]
    result = context.runner.invoke(cli_module.app, args)
    context.cli_result = result
    if getattr(context, "_original_build_service", None) is not None:
        cli_module.build_evaluation_service = context._original_build_service


@then('the verdict should be "{expected}"')
def step_assert_verdict(context, expected: str) -> None:
    assert context.cli_result.exit_code == 0, context.cli_result.output
    payload = json.loads(context.cli_result.output)
    assert payload["verdict"] == expected, payload
    context.last_payload = payload


@then("audit and manifest artifacts should exist")
def step_assert_artifacts(context) -> None:
    details = context.last_payload.get("details", {})
    audit_path = details.get("audit_path")
    manifest_path = details.get("manifest_path")
    assert audit_path, details
    assert manifest_path, details
    assert Path(audit_path).exists(), audit_path
    assert Path(manifest_path).exists(), manifest_path


@then("replaying the audit should include the promise id")
def step_replay_audit(context) -> None:
    details = context.last_payload.get("details", {})
    audit_path = details.get("audit_path")
    assert audit_path, details
    args = ["replay-audit", audit_path, "--json"]
    result = context.runner.invoke(cli_module.app, args)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    ledger = payload.get("ledger", {})
    assert "llm-input-logging" in ledger, payload
