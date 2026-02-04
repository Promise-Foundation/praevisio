from __future__ import annotations

import json
import socket
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


class EgressAnalyzer:
    def analyze(self, path: str) -> StaticAnalysisResult:
        socket.create_connection(("example.com", 80), timeout=0.1)
        return StaticAnalysisResult(total_llm_calls=0, violations=0, coverage=0.0, findings=[])


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


def _write_config(repo_path: Path) -> Path:
    config_path = repo_path / ".praevisio.yaml"
    config_path.write_text(
        "\n".join(
            [
                "evaluation:",
                "  promise_id: llm-input-logging",
                "  threshold: 0.80",
                "  abductio_credits: 8",
                "  pytest_targets:",
                "    - tests/test_logging.py",
                "  semgrep_rules_path: rules.yaml",
                "  run_dir: .praevisio/runs",
                "hooks: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _latest_run_dir(repo_path: Path) -> Path:
    runs_dir = repo_path / ".praevisio/runs"
    candidates = [p for p in runs_dir.iterdir() if p.is_dir()]
    assert candidates, f"No runs under {runs_dir}"
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _patch_service(context) -> None:
    service = EvaluationService(
        analyzer=context.analyzer,
        test_runner=context.test_runner,
        promise_loader=context.promise_loader,
    )
    context._original_build_service = getattr(cli_module, "build_evaluation_service", None)
    cli_module.build_evaluation_service = lambda: service


def _restore_service(context) -> None:
    if getattr(context, "_original_build_service", None) is not None:
        cli_module.build_evaluation_service = context._original_build_service


def _run_offline(context, json_output: bool) -> None:
    _patch_service(context)
    args = [
        "evaluate-commit",
        str(context.repo_path),
        "--config",
        str(context.config_path),
        "--offline",
    ]
    if json_output:
        args.append("--json")
    result = context.runner.invoke(cli_module.app, args)
    context.cli_result = result
    _restore_service(context)


@given("a repository with runnable local evidence tools")
def step_repo_with_tools(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-offline-"))
    (repo_dir / "tests").mkdir(parents=True, exist_ok=True)
    (repo_dir / "tests/test_logging.py").write_text(
        "def test_smoke():\n    assert True\n", encoding="utf-8"
    )
    context.repo_path = repo_dir
    context.config_path = _write_config(repo_dir)
    context.runner = CliRunner()
    context.analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    context.test_runner = FakeTestRunner(exit_code=0)
    context.promise_loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))


@given("offline mode is enabled")
def step_offline_enabled(context) -> None:
    context.offline_enabled = True


@given("a component that attempts an outbound network request")
def step_component_network_request(context) -> None:
    context.analyzer = EgressAnalyzer()


@when('I run "praevisio evaluate-commit . --config .praevisio.yaml --offline"')
def step_run_offline(context) -> None:
    _run_offline(context, json_output=False)


@when('I run "praevisio evaluate-commit . --config .praevisio.yaml --offline --json"')
def step_run_offline_json(context) -> None:
    _run_offline(context, json_output=True)


@then("the evaluation should complete successfully")
def step_eval_success(context) -> None:
    assert context.cli_result.exit_code == 0, context.cli_result.output


@then("the manifest should record \"egress_policy\" as \"offline\"")
def step_manifest_egress_policy(context) -> None:
    run_dir = _latest_run_dir(context.repo_path)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    metadata = manifest.get("metadata") or {}
    assert metadata.get("egress_policy") == "offline"


@then("the error should mention \"egress violation\"")
def step_error_mentions_egress(context) -> None:
    assert "egress violation" in context.cli_result.output.lower()


@then('the audit file should include an "egress_enforcement" record')
def step_audit_includes_enforcement(context) -> None:
    run_dir = _latest_run_dir(context.repo_path)
    audit_payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
    events = audit_payload.get("events") if isinstance(audit_payload, dict) else audit_payload
    assert any(e.get("event_type") == "egress_enforcement" for e in events), events


@then('the record should include the enforcement outcome "blocked_or_none_attempted"')
def step_audit_enforcement_outcome(context) -> None:
    run_dir = _latest_run_dir(context.repo_path)
    audit_payload = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
    events = audit_payload.get("events") if isinstance(audit_payload, dict) else audit_payload
    entry = next(e for e in events if e.get("event_type") == "egress_enforcement")
    payload = entry.get("payload") or {}
    assert payload.get("outcome") == "blocked_or_none_attempted"
