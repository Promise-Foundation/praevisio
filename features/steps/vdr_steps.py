from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from behave import given, when, then
from typer.testing import CliRunner

import praevisio.presentation.cli as cli_module


@given('a VDR export directory "vdr_export/"')
def step_vdr_export(context) -> None:
    base_dir = Path(tempfile.mkdtemp(prefix="praevisio-vdr-"))
    vdr_dir = base_dir / "vdr_export"
    vdr_dir.mkdir(parents=True, exist_ok=True)
    (vdr_dir / "contracts").mkdir(parents=True, exist_ok=True)
    (vdr_dir / "contracts" / "contract_a.txt").write_text(
        "contract A contents", encoding="utf-8"
    )
    (vdr_dir / "nda.pdf").write_text("nda contents", encoding="utf-8")
    context.vdr_dir = vdr_dir
    context.base_dir = base_dir
    context.runner = CliRunner()


@given("ingestion is enabled")
def step_ingestion_enabled(context) -> None:
    context.ingestion_enabled = True
    if getattr(context, "vdr_dir", None) is not None and getattr(context, "base_dir", None) is not None:
        evidence_dir = context.base_dir / "evidence"
        runner = getattr(context, "runner", CliRunner())
        result = runner.invoke(
            cli_module.app, ["ingest", str(context.vdr_dir), "--into", str(evidence_dir)]
        )
        context.cli_result = result
        context.manifest_path = evidence_dir / "manifest.json"
        context.result = SimpleNamespace(details={"manifest_path": str(context.manifest_path)})


@when('I run "praevisio ingest vdr_export/ --into evidence/"')
def step_run_ingest(context) -> None:
    evidence_dir = context.base_dir / "evidence"
    args = ["ingest", str(context.vdr_dir), "--into", str(evidence_dir)]
    result = context.runner.invoke(cli_module.app, args)
    context.cli_result = result
    context.manifest_path = evidence_dir / "manifest.json"
    context.result = SimpleNamespace(details={"manifest_path": str(context.manifest_path)})


@then('each ingested document should have an "evidence_id"')
def step_evidence_ids(context) -> None:
    manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts", [])
    assert artifacts, manifest
    assert all(item.get("evidence_id") for item in artifacts), artifacts


@then("each should have a SHA-256 hash recorded in the manifest")
def step_hashes(context) -> None:
    manifest = json.loads(context.manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts", [])
    assert all(item.get("sha256") for item in artifacts), artifacts


@then('each evidence artifact should include "original_path"')
def step_original_path(context) -> None:
    manifest = json.loads(context.manifest)
    artifacts = manifest.get("artifacts", [])
    assert all(item.get("original_path") for item in artifacts), artifacts


@then('each artifact should include "ingested_at"')
def step_ingested_at(context) -> None:
    manifest = json.loads(context.manifest)
    artifacts = manifest.get("artifacts", [])
    assert all(item.get("ingested_at") for item in artifacts), artifacts
