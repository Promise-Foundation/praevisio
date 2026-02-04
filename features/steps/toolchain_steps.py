from __future__ import annotations

import json
import tempfile
import random
from dataclasses import dataclass, replace
from pathlib import Path

from behave import given, when, then

from praevisio.application.evaluation_service import EvaluationService
from praevisio.domain.entities import StaticAnalysisResult
from praevisio.domain.evaluation_config import EvaluationConfig
from praevisio.domain.models import Promise


@dataclass
class FakeAnalyzer:
    result: StaticAnalysisResult

    def analyze(self, path: str) -> StaticAnalysisResult:
        return self.result


@dataclass
class FlakyTestRunner:
    calls: int = 0

    def run(self, path: str, args: list[str]) -> int:
        self.calls += 1
        return 0 if self.calls == 1 else 1


@dataclass
class FixedTestRunner:
    exit_code: int = 0

    def run(self, path: str, args: list[str]) -> int:
        return self.exit_code


@dataclass
class RandomizedAnalyzer:
    def analyze(self, path: str) -> StaticAnalysisResult:
        return StaticAnalysisResult(
            total_llm_calls=1,
            violations=0,
            coverage=random.random(),
            findings=[],
        )


@dataclass
class FakePromiseLoader:
    promise: Promise

    def load(self, promise_id: str) -> Promise:
        return self.promise


@then('the manifest should include "{field}"')
def step_manifest_includes(context, field: str) -> None:
    manifest_text = getattr(context, "manifest", None)
    if not manifest_text:
        manifest_path = getattr(context, "manifest_path", None)
        assert manifest_path, "Missing manifest_path"
        manifest_text = Path(manifest_path).read_text(encoding="utf-8")
    assert f"\"{field}\"" in manifest_text, manifest_text


@given("my current toolchain versions differ from the recorded manifest")
def step_toolchain_differs(context) -> None:
    manifest_path = getattr(context, "manifest_path", None)
    if manifest_path is None:
        manifest_path = Path(context.result.details["manifest_path"])
        context.manifest_path = manifest_path
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    metadata = manifest.get("metadata") or {}
    metadata["python_version"] = "0.0.0"
    metadata["praevisio_version"] = "0.0.0"
    metadata["tool_versions"] = {"pytest": "0.0.0"}
    manifest["metadata"] = metadata
    Path(manifest_path).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    context.use_cli_replay = True


@given("strict determinism is enabled for replay")
def step_strict_replay(context) -> None:
    context.use_cli_replay = True
    context.replay_strict = True


@then("the replay should produce a determinism warning or fail")
def step_replay_warning_or_fail(context) -> None:
    result = getattr(context, "replay_cli_result", None)
    assert result is not None, "Missing replay_cli_result"
    output = result.output.lower()
    assert result.exit_code != 0 or "toolchain mismatch" in output


@then('the output should mention "{text}"')
def step_output_mentions(context, text: str) -> None:
    output = getattr(context, "replay_output", "")
    assert text.lower() in output.lower(), output


@then("the replay should fail due to determinism mismatch")
def step_replay_fail_determinism(context) -> None:
    result = getattr(context, "replay_cli_result", None)
    assert result is not None, "Missing replay_cli_result"
    assert result.exit_code != 0, result.output


@given("an evidence collector that produces nondeterministic output")
def step_nondeterministic_collector(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-nondeterministic-"))
    context.repo_path = repo_dir
    context.analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    context.test_runner = FlakyTestRunner()
    context.promise_loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))
    context.eval_config = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.1,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        determinism_runs=2,
        determinism_mode="warn",
    )


@given("an evidence collector that uses randomness unless seeded")
def step_randomized_collector(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-randomized-"))
    context.repo_path = repo_dir
    context.analyzer = RandomizedAnalyzer()
    context.test_runner = FixedTestRunner()
    context.promise_loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))
    context.eval_config = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.1,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        determinism_runs=2,
        determinism_mode="warn",
    )


@given('determinism mode is "{mode}"')
def step_set_determinism_mode(context, mode: str) -> None:
    context.eval_config = replace(context.eval_config, determinism_mode=mode)


@given("determinism seed is set to {seed:d}")
def step_set_determinism_seed(context, seed: int) -> None:
    context.eval_config = replace(context.eval_config, determinism_seed=seed)


@when("I run evaluation with nondeterministic evidence")
def step_run_nondeterministic_eval(context) -> None:
    service = EvaluationService(
        analyzer=context.analyzer,
        test_runner=context.test_runner,
        promise_loader=context.promise_loader,
    )
    context.result = service.evaluate_path(str(context.repo_path), config=context.eval_config)


@then('the report should include an anomaly "{name}"')
def step_report_includes_anomaly(context, name: str) -> None:
    anomalies = context.result.details.get("anomalies", [])
    assert name in anomalies, anomalies


@then("the anomaly should include an operator action")
def step_anomaly_action(context) -> None:
    actions = context.result.details.get("anomaly_actions", {})
    if "toolchain_nondeterminism" in actions:
        assert actions.get("toolchain_nondeterminism"), actions
        return
    assert actions, actions


@then("the evaluation should fail closed")
def step_eval_fail_closed(context) -> None:
    assert context.result.verdict == "error", context.result


@then("the determinism checks should pass")
def step_determinism_pass(context) -> None:
    determinism = context.result.details.get("determinism", {})
    anomalies = context.result.details.get("anomalies", [])
    assert not determinism.get("mismatch"), determinism
    assert "toolchain_nondeterminism" not in anomalies, anomalies
