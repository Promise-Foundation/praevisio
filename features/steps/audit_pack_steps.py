from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from behave import given, when, then
from typer.testing import CliRunner

import praevisio.presentation.cli as cli_module
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
class FakeTestRunner:
    exit_code: int = 0

    def run(self, path: str, args: list[str]) -> int:
        return self.exit_code


@dataclass
class FakePromiseLoader:
    promise: Promise

    def load(self, promise_id: str) -> Promise:
        return self.promise


@given("an evaluation run completed with report signing enabled")
def step_eval_run_completed(context) -> None:
    repo_dir = Path(tempfile.mkdtemp(prefix="praevisio-auditpack-"))
    analyzer = FakeAnalyzer(
        StaticAnalysisResult(total_llm_calls=1, violations=0, coverage=1.0, findings=[])
    )
    runner = FakeTestRunner(exit_code=0)
    loader = FakePromiseLoader(Promise(id="llm-input-logging", statement="test"))
    service = EvaluationService(analyzer=analyzer, test_runner=runner, promise_loader=loader)
    config = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.1,
        pytest_targets=[],
        semgrep_rules_path="rules.yaml",
        run_dir=".praevisio/runs",
    )
    result = service.evaluate_path(str(repo_dir), config=config)
    run_id = result.details["run_id"]
    run_root = Path(repo_dir) / config.run_dir / run_id
    target_run_id = "RUN123"
    target_root = Path(repo_dir) / config.run_dir / target_run_id
    target_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(run_root), str(target_root))
    manifest_path = target_root / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        metadata = manifest.get("metadata") or {}
        metadata["run_id"] = target_run_id
        manifest["metadata"] = metadata
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    context.repo_dir = repo_dir
    context.runs_dir = Path(repo_dir) / config.run_dir
    context.run_id = target_run_id
    context.runner = CliRunner()
    context.bundle_path = Path(repo_dir) / "auditpack.zip"
    if context.bundle_path.exists():
        context.bundle_path.unlink()


@when('I run "praevisio export --run RUN123 --out auditpack.zip"')
def step_run_export(context) -> None:
    context.bundle_path = Path(context.repo_dir) / "auditpack.zip"
    args = [
        "export",
        "--run",
        context.run_id,
        "--out",
        str(context.bundle_path),
        "--runs-dir",
        str(context.runs_dir),
    ]
    context.export_result = context.runner.invoke(cli_module.app, args)


@then('the bundle should include "{filename}"')
def step_bundle_includes(context, filename: str) -> None:
    assert context.bundle_path.exists(), context.bundle_path
    with zipfile.ZipFile(context.bundle_path, "r") as zf:
        names = set(zf.namelist())
    assert filename in names, f"{filename} not in bundle: {names}"


@then('it should include "audit.jsonl"')
def step_bundle_includes_audit_jsonl(context) -> None:
    step_bundle_includes(context, "audit.jsonl")


@then('it should include "report.pdf" or "report.json"')
def step_bundle_includes_report(context) -> None:
    with zipfile.ZipFile(context.bundle_path, "r") as zf:
        names = set(zf.namelist())
    assert ("report.pdf" in names) or ("report.json" in names), names


@then("it should include signature files")
def step_bundle_includes_signatures(context) -> None:
    with zipfile.ZipFile(context.bundle_path, "r") as zf:
        names = set(zf.namelist())
    sigs = [n for n in names if n.endswith(".sig")]
    assert sigs, f"No signature files found in bundle: {names}"


@when('I run "praevisio verify auditpack.zip"')
def step_run_verify(context) -> None:
    if not context.bundle_path.exists():
        args = [
            "export",
            "--run",
            context.run_id,
            "--out",
            str(context.bundle_path),
            "--runs-dir",
            str(context.runs_dir),
        ]
        context.export_result = context.runner.invoke(cli_module.app, args)
    args = ["verify", str(context.bundle_path)]
    context.verify_result = context.runner.invoke(cli_module.app, args)


@then("bundle verification should succeed")
def step_verify_succeeds(context) -> None:
    assert context.verify_result.exit_code == 0, context.verify_result.output


@then('it should report "integrity_ok"')
def step_verify_reports_ok(context) -> None:
    assert "integrity_ok" in context.verify_result.output


@given('I modify one file in "auditpack.zip"')
def step_modify_bundle(context) -> None:
    if not context.bundle_path.exists():
        args = [
            "export",
            "--run",
            context.run_id,
            "--out",
            str(context.bundle_path),
            "--runs-dir",
            str(context.runs_dir),
        ]
        context.export_result = context.runner.invoke(cli_module.app, args)
    original = context.bundle_path
    tampered = original.with_suffix(".tampered.zip")
    with zipfile.ZipFile(original, "r") as zin, zipfile.ZipFile(
        tampered, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "report.json":
                data = data + b"\n"
            zout.writestr(item, data)
    tampered.replace(original)


@then("bundle verification should fail")
def step_verify_fails(context) -> None:
    assert context.verify_result.exit_code != 0, context.verify_result.output


@then("the output should mention which integrity check failed")
def step_verify_mentions_failure(context) -> None:
    output = context.verify_result.output.lower()
    assert any(
        key in output
        for key in ["hash mismatch", "signature", "hash chain", "missing artifact"]
    ), output
