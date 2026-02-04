from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from behave import given, when, then

from praevisio.application.decision_service import build_decision
from praevisio.application.evaluation_service import EvaluationService
from praevisio.domain.entities import StaticAnalysisResult
from praevisio.domain.evaluation_config import EvaluationConfig
from praevisio.domain.models import Promise


@dataclass
class FakeTestRunner:
    exit_code: int = 0

    def run(self, path: str, args: list[str]) -> int:
        return self.exit_code


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


def _base_config() -> EvaluationConfig:
    return EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.2,
        pytest_targets=["tests/test_logging.py"],
        semgrep_rules_path="rules.yaml",
        run_dir=".praevisio/runs",
    )


@given("a repo with passing tests")
def step_repo_passing_tests(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-evidence-"))
    context.repo_path = repo_dir
    context.test_runner = FakeTestRunner(exit_code=0)
    context.analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    context.promise_loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))


@given("a repo with semgrep rules")
def step_repo_semgrep(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-evidence-"))
    context.repo_path = repo_dir
    context.test_runner = FakeTestRunner(exit_code=0)
    context.analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=5, violations=1, coverage=0.8, findings=[])
    )
    context.promise_loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))


@given("a completed evaluation run")
def step_completed_run(context) -> None:
    step_repo_passing_tests(context)
    service = EvaluationService(
        analyzer=context.analyzer,
        test_runner=context.test_runner,
        promise_loader=context.promise_loader,
    )
    result = service.evaluate_path(str(context.repo_path), config=_base_config())
    context.result = result
    details = result.details
    audit_path = details.get("audit_path")
    manifest_path = details.get("manifest_path")
    if audit_path:
        context.audit_path = Path(audit_path)
    if manifest_path:
        context.manifest_path = Path(manifest_path)


@when("I run evaluation")
def step_run_evaluation(context) -> None:
    synthetic = getattr(context, "synthetic_evaluation", None)
    if synthetic is not None:
        result, evaluation = synthetic.build()
        context.result = result
        context.evaluation = evaluation
        context.decision = build_decision(
            result,
            evaluation,
            enforcement_mode="ci-gate",
            fail_on_violation=True,
        )
        manifest_metadata = getattr(synthetic, "manifest_metadata", None)
        if manifest_metadata is not None:
            run_dir = Path(tempfile.mkdtemp(prefix="praevisio-manifest-"))
            manifest_path = run_dir / "manifest.json"
            manifest = {"metadata": manifest_metadata}
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            result.details["manifest_path"] = str(manifest_path)
            result.details["manifest_sha256"] = digest
        payload = {
            "credence": result.credence,
            "verdict": result.verdict,
            "details": result.details,
        }
        exit_code = 1 if result.verdict in {"red", "error"} else 0
        context.cli_result = SimpleNamespace(
            exit_code=exit_code,
            output=json.dumps(payload),
        )
        return
    service = EvaluationService(
        analyzer=context.analyzer,
        test_runner=context.test_runner,
        promise_loader=context.promise_loader,
    )
    context.result = service.evaluate_path(str(context.repo_path), config=_base_config())


@then("pytest evidence should be stored")
def step_pytest_evidence_stored(context) -> None:
    refs = context.result.details.get("evidence_refs", {})
    pytest_refs = refs.get("pytest", [])
    assert pytest_refs, "No pytest evidence refs found"


@then("the evidence should include exit code")
def step_pytest_exit_code(context) -> None:
    manifest_path = context.result.details.get("manifest_path")
    assert manifest_path, "Missing manifest_path"
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts", [])
    pytest_artifacts = [a for a in artifacts if a.get("kind") == "pytest"]
    assert pytest_artifacts, "No pytest artifacts listed in manifest"
    pytest_path = Path(manifest_path).parent / pytest_artifacts[0]["path"]
    payload = json.loads(pytest_path.read_text(encoding="utf-8"))
    assert "exit_code" in payload


@then("semgrep evidence should be stored")
def step_semgrep_evidence_stored(context) -> None:
    refs = context.result.details.get("evidence_refs", {})
    semgrep_refs = refs.get("semgrep", [])
    assert semgrep_refs, "No semgrep evidence refs found"


@then("the evidence should include coverage metrics")
def step_semgrep_coverage(context) -> None:
    evidence = context.result.details.get("evidence", {})
    assert "semgrep_coverage" in evidence
    assert "violations_found" in evidence


@when("I inspect the manifest")
def step_inspect_manifest(context) -> None:
    manifest_path = context.result.details.get("manifest_path")
    assert manifest_path, "Missing manifest_path"
    context.manifest = Path(manifest_path).read_text(encoding="utf-8")


@then("it should list all evidence artifacts")
def step_manifest_artifacts(context) -> None:
    assert '"artifacts"' in context.manifest


@then("each artifact should have a SHA-256 hash")
def step_manifest_hashes(context) -> None:
    assert '"sha256"' in context.manifest
