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
class FakeTestRunner:
    exit_code: int = 0

    def run(self, path: str, args: list[str]) -> int:
        return self.exit_code


@dataclass
class FakePromiseLoader:
    promise: Promise

    def load(self, promise_id: str) -> Promise:
        return self.promise


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@given("a fresh tutorial repository")
def step_fresh_repo(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-tutorial-full-"))
    context.repo_path = repo_dir
    context.runner = CliRunner()
    context.analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    context.test_runner = FakeTestRunner(exit_code=0)
    context.promise_loader = FakePromiseLoader(
        Promise(id="llm-input-logging", statement="All LLM input prompts must be logged.")
    )


@given("I create the boundary module")
def step_create_boundary(context) -> None:
    content = (
        "from __future__ import annotations\n"
        "from pathlib import Path\n\n"
        "def log(prompt: str, log_path: Path) -> None:\n"
        "    with log_path.open(\"a\", encoding=\"utf-8\") as f:\n"
        "        f.write(prompt + \"\\n\")\n\n"
        "def call_llm(prompt: str) -> str:\n"
        "    return f\"echo:{prompt}\"\n\n"
        "def generate(prompt: str, log_path: Path) -> str:\n"
        "    log(prompt, log_path)\n"
        "    return call_llm(prompt)\n"
    )
    _write_file(context.repo_path / "app/src/llm_gateway.py", content)


@given("I create the test file")
def step_create_test(context) -> None:
    content = (
        "from app.src.llm_gateway import generate\n\n"
        "def test_generate_logs_and_calls(tmp_path):\n"
        "    log_path = tmp_path / \"llm_log.txt\"\n"
        "    assert generate(\"hello\", log_path) == \"echo:hello\"\n"
    )
    _write_file(context.repo_path / "tests/test_logging.py", content)


@given("I create the semgrep rules")
def step_create_rules(context) -> None:
    rules = (
        "rules:\n"
        "  - id: llm-call-site\n"
        "    languages: [python]\n"
        "    message: LLM call site detected\n"
        "    severity: INFO\n"
        "    patterns:\n"
        "      - pattern: call_llm($PROMPT)\n\n"
        "  - id: llm-call-must-log\n"
        "    languages: [python]\n"
        "    message: LLM call detected without prior logging\n"
        "    severity: ERROR\n"
        "    patterns:\n"
        "      - pattern: call_llm($PROMPT)\n"
        "      - pattern-not-inside: |\n"
        "          log($PROMPT, $LOG_PATH)\n"
        "          ...\n"
        "          call_llm($PROMPT)\n"
    )
    _write_file(context.repo_path / "governance/evidence/semgrep_rules.yaml", rules)


@given("I create the promise file")
def step_create_promise(context) -> None:
    promise = (
        "id: llm-input-logging\n"
        "version: 0.1.0\n"
        "domain: /llm/logging\n"
        "statement: All LLM input prompts must be logged at the boundary.\n"
        "critical: true\n"
        "success_criteria:\n"
        "  credence_threshold: 0.95\n"
        "  evidence_types:\n"
        "    - direct_observational\n"
        "    - procedural\n"
        "parameters: {}\n"
    )
    _write_file(context.repo_path / "governance/promises/llm-input-logging.yaml", promise)


@given("I create the config file")
def step_create_config(context) -> None:
    config = (
        "evaluation:\n"
        "  promise_id: llm-input-logging\n"
        "  threshold: 0.95\n"
        "  abductio_credits: 8\n"
        "  pytest_targets:\n"
        "    - tests/test_logging.py\n"
        "  semgrep_rules_path: governance/evidence/semgrep_rules.yaml\n"
        "  semgrep_callsite_rule_id: llm-call-site\n"
        "  semgrep_violation_rule_id: llm-call-must-log\n"
        "hooks: []\n"
    )
    _write_file(context.repo_path / ".praevisio.yaml", config)


@when('I run "praevisio evaluate-commit . --config .praevisio.yaml --json"')
def step_run_eval(context) -> None:
    service = EvaluationService(
        analyzer=context.analyzer,
        test_runner=context.test_runner,
        promise_loader=context.promise_loader,
    )
    context._original_build_service = getattr(cli_module, "build_evaluation_service", None)
    cli_module.build_evaluation_service = lambda: service
    args = [
        "evaluate-commit",
        str(context.repo_path),
        "--config",
        str(context.repo_path / ".praevisio.yaml"),
        "--json",
    ]
    context.cli_result = context.runner.invoke(cli_module.app, args)
    if getattr(context, "_original_build_service", None) is not None:
        cli_module.build_evaluation_service = context._original_build_service


@then("the evaluation should pass")
def step_eval_pass(context) -> None:
    assert context.cli_result.exit_code == 0, context.cli_result.output


@then("the audit file should exist")
def step_audit_exists(context) -> None:
    details = context.last_payload.get("details", {})
    audit_path = details.get("audit_path")
    assert audit_path and Path(audit_path).exists(), audit_path


@then("I can replay the audit")
def step_replay_audit(context) -> None:
    details = context.last_payload.get("details", {})
    audit_path = details.get("audit_path")
    args = ["replay-audit", audit_path, "--json"]
    result = context.runner.invoke(cli_module.app, args)
    assert result.exit_code == 0, result.output


@given("a tutorial repository with logging boundary")
def step_repo_with_boundary(context) -> None:
    step_fresh_repo(context)
    step_create_boundary(context)
    step_create_test(context)
    step_create_rules(context)
    step_create_promise(context)
    step_create_config(context)


@when("I remove the log call from the boundary")
def step_remove_log(context) -> None:
    content = (
        "from __future__ import annotations\n"
        "from pathlib import Path\n\n"
        "def log(prompt: str, log_path: Path) -> None:\n"
        "    with log_path.open(\"a\", encoding=\"utf-8\") as f:\n"
        "        f.write(prompt + \"\\n\")\n\n"
        "def call_llm(prompt: str) -> str:\n"
        "    return f\"echo:{prompt}\"\n\n"
        "def generate(prompt: str, log_path: Path) -> str:\n"
        "    return call_llm(prompt)\n"
    )
    _write_file(context.repo_path / "app/src/llm_gateway.py", content)
    context.analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=1, coverage=0.0, findings=[])
    )


@then("the evaluation should fail")
def step_eval_fail(context) -> None:
    assert context.cli_result.exit_code == 0, context.cli_result.output


@then("semgrep should report 1 violation")
def step_semgrep_violation(context) -> None:
    payload = json.loads(context.cli_result.output)
    evidence = payload["details"]["evidence"]
    assert evidence["violations_found"] == 1, evidence
