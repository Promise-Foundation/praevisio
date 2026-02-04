from __future__ import annotations

"""Typer-based command-line interface for praevisio.

Commands map to application services. Run `python -m praevisio --help` to see
available commands.
"""

import hashlib
import json
import stat
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import replace
from typing import Optional
import typer

from abductio_core.application.use_cases.replay_session import replay_session

from ..application.engine import PraevisioEngine
from ..application.decision_service import build_decision, add_notification
from ..application.evaluation_service import EvaluationService
from ..application.installation_service import InstallationService
from ..infrastructure.filesystem import LocalFileSystemService
from ..infrastructure.config import YamlConfigLoader
from ..infrastructure.toolchain import compare_toolchain, current_toolchain_metadata
from ..infrastructure.audit_pack import export_audit_pack, verify_audit_pack


app = typer.Typer(add_completion=False, no_args_is_help=True)


def build_evaluation_service() -> EvaluationService:
    return EvaluationService()


def build_engine() -> PraevisioEngine:
    loader = YamlConfigLoader()
    fs = LocalFileSystemService()
    return PraevisioEngine(loader, fs, evaluation_service=build_evaluation_service())


def load_configuration(engine: PraevisioEngine, path: str):
    try:
        return engine.load_config(path)
    except FileNotFoundError:
        typer.echo(f"[praevisio] Config not found: {path}")
        raise typer.Exit(code=2)


def _manifest_metadata_for_audit(audit_file: Path) -> Optional[dict]:
    manifest_path = audit_file.parent / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest.get("metadata") or {}


@app.command()
def install(config_path: str = ".praevisio.yaml") -> None:
    fs = LocalFileSystemService()
    installer = InstallationService(fs, config_path)
    path = installer.install()
    typer.echo(f"Installed default config at {path}")


@app.command("pre-commit")
def pre_commit(
    path: str = typer.Argument(".", help="Path to the repository/commit to evaluate."),
    threshold: Optional[float] = typer.Option(
        None, "--threshold", help="Credence threshold required to pass the pre-commit gate."
    ),
    config_path: str = typer.Option(
        ".praevisio.yaml", "--config", help="Path to Praevisio configuration file."
    ),
) -> None:
    """Local governance gate to block commits when credence is below threshold."""
    engine = build_engine()
    config = load_configuration(engine, config_path)
    evaluation = config.evaluation
    gate = engine.pre_commit_gate(path, evaluation, threshold_override=threshold)
    result = gate.evaluation
    if result.verdict == "error":
        typer.echo("[praevisio][pre-commit] ❌ Evaluation error. Commit aborted.")
        raise typer.Exit(code=1)
    if gate.should_fail:
        typer.echo("[praevisio][pre-commit] ❌ Critical promises not satisfied. Commit aborted.")
        raise typer.Exit(code=1)
    typer.echo("[praevisio][pre-commit] ✅ All critical promises satisfied.")


@app.command("evaluate-commit")
def evaluate_commit_cmd(
    path: str,
    json_output: bool = typer.Option(
        False,
        "--json-output",
        "--json",
        help="Print structured JSON output instead of plain text.",
    ),
    threshold: Optional[float] = typer.Option(
        None, "--threshold", help="Credence threshold required to pass the evaluation."
    ),
    config_path: str = typer.Option(
        ".praevisio.yaml", "--config", help="Path to Praevisio configuration file."
    ),
    offline: bool = typer.Option(
        False, "--offline", help="Run in offline mode (block network egress)."
    ),
) -> None:
    """Evaluate a single commit directory and print credence and verdict."""
    engine = build_engine()
    config = load_configuration(engine, config_path)
    evaluation = config.evaluation
    evaluation = engine.apply_threshold(evaluation, threshold, evaluation.severity)
    evaluation = replace(evaluation, offline=offline or evaluation.offline)
    result = engine.evaluate(path, evaluation)
    _write_decision(
        result,
        evaluation,
        enforcement_mode="evaluate-commit",
        fail_on_violation=True,
        include_notification=False,
    )
    if json_output:
        typer.echo(json.dumps({
            "credence": result.credence,
            "verdict": result.verdict,
            "details": result.details,
        }, indent=2))
    else:
        credence_display = "n/a" if result.credence is None else f"{result.credence:.3f}"
        typer.echo(f"Credence: {credence_display}")
        typer.echo(f"Verdict: {result.verdict}")
        if result.verdict == "error":
            egress_error = result.details.get("egress_error")
            if egress_error:
                typer.echo(f"[praevisio][egress] {egress_error}")
    if result.verdict in {"red", "error"}:
        raise typer.Exit(code=1)


@app.command("ci-gate")
def ci_gate(
    path: str = typer.Argument(".", help="Path to the target repository/commit."),
    severity: Optional[str] = typer.Option(
        None, "--severity", help="Severity level to enforce."
    ),
    fail_on_violation: bool = typer.Option(
        False,
        "--enforce",
        "--fail-on-violation",
        help="Report-only by default; use to fail CI on red/error verdicts.",
    ),
    output: str = typer.Option(
        "logs/ci-gate-report.json",
        "--output",
        help="Where to write JSON report of evaluated promises.",
    ),
    threshold: Optional[float] = typer.Option(
        None, "--threshold", help="Credence threshold for passing high-severity promises."
    ),
    config_path: str = typer.Option(
        ".praevisio.yaml", "--config", help="Path to Praevisio configuration file."
    ),
    offline: bool = typer.Option(
        False, "--offline", help="Run in offline mode (block network egress)."
    ),
) -> None:
    """Run Praevisio as a CI governance gate."""
    engine = build_engine()
    config = load_configuration(engine, config_path)
    evaluation = config.evaluation
    evaluation = replace(evaluation, offline=offline or evaluation.offline)
    promise_ids = list(getattr(config, "promises", []) or [])
    if not promise_ids:
        gate = engine.ci_gate(
            path,
            evaluation,
            severity=severity,
            threshold_override=threshold,
            fail_on_violation=fail_on_violation,
        )
        effective = engine.apply_threshold(evaluation, threshold, severity)
        _write_decision(
            gate.evaluation,
            effective,
            enforcement_mode="ci-gate",
            fail_on_violation=fail_on_violation,
            include_notification=True,
        )
        report = [gate.report_entry]

        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        if gate.should_fail:
            typer.echo("[praevisio][ci-gate] ❌ GATE FAILED")
            raise typer.Exit(code=1)

        typer.echo("[praevisio][ci-gate] ✅ GATE PASSED")
        return

    results = []
    should_fail = False
    for promise_id in promise_ids:
        eval_for_promise = replace(evaluation, promise_id=promise_id)
        gate = engine.ci_gate(
            path,
            eval_for_promise,
            severity=severity,
            threshold_override=threshold,
            fail_on_violation=fail_on_violation,
        )
        effective = engine.apply_threshold(eval_for_promise, threshold, severity)
        _write_decision(
            gate.evaluation,
            effective,
            enforcement_mode="ci-gate",
            fail_on_violation=fail_on_violation,
            include_notification=True,
        )
        results.append(gate.report_entry)
        if gate.should_fail:
            should_fail = True

    overall_verdict = "block" if should_fail else "allow"
    policy_payload = {
        "promises": promise_ids,
        "severity": severity or evaluation.severity,
        "threshold": threshold or evaluation.threshold,
        "thresholds": dict(evaluation.thresholds),
        "fail_on_violation": fail_on_violation,
    }
    policy_id = hashlib.sha256(
        json.dumps(policy_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    report = {
        "overall_verdict": overall_verdict,
        "policy_id": policy_id,
        "results": results,
    }

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if should_fail:
        typer.echo("[praevisio][ci-gate] ❌ GATE FAILED")
        raise typer.Exit(code=1)

    typer.echo("[praevisio][ci-gate] ✅ GATE PASSED")


@app.command("install-hooks")
def install_hooks(
    git_dir: str = typer.Option(
        ".", "--git-dir", help="Root of the git repository where hooks should be installed."
    )
) -> None:
    """Install a git pre-commit hook that runs `praevisio pre-commit`."""
    repo_root = Path(git_dir).resolve()
    hooks_dir = repo_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "pre-commit"
    script = """#!/usr/bin/env sh
# Praevisio governance pre-commit hook

praevisio pre-commit
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
  echo "[praevisio][pre-commit] ❌ Critical promises not satisfied. Commit aborted."
  exit "$STATUS"
fi
exit 0
"""
    hook_path.write_text(script, encoding="utf-8")
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    typer.echo(f"Installed pre-commit hook at {hook_path}")


@app.command("ingest")
def ingest(
    source_dir: str = typer.Argument(..., help="Path to VDR export directory."),
    into: str = typer.Option("evidence", "--into", help="Destination evidence directory."),
) -> None:
    """Ingest a VDR export directory into an evidence store with provenance."""
    source = Path(source_dir)
    if not source.exists():
        typer.echo(f"[praevisio][ingest] Source not found: {source}")
        raise typer.Exit(code=2)
    dest = Path(into)
    dest.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        data = item.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        evidence_id = f"evidence:{sha}"
        rel_path = item.relative_to(source).as_posix()
        dest_path = dest / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        artifacts.append(
            {
                "evidence_id": evidence_id,
                "sha256": sha,
                "path": str(dest_path.relative_to(dest)),
                "original_path": rel_path,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    manifest = {
        "metadata": {"source": "VDR_IMPORT"},
        "artifacts": artifacts,
    }
    manifest_path = dest / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    typer.echo(f"[praevisio][ingest] Ingested {len(artifacts)} artifacts.")


@app.command("replay-audit")
def replay_audit(
    audit_path: Optional[str] = typer.Argument(
        None, help="Path to an Abductio audit JSON file."
    ),
    latest: bool = typer.Option(
        False, "--latest", help="Replay the most recent audit under the runs directory."
    ),
    runs_dir: str = typer.Option(
        ".praevisio/runs", "--runs-dir", help="Base directory for run artifacts."
    ),
    strict_determinism: bool = typer.Option(
        False,
        "--strict-determinism",
        help="Fail replay when toolchain differs from the recorded manifest.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json-output",
        "--json",
        help="Print structured JSON output instead of plain text.",
    ),
) -> None:
    """Replay an Abductio audit trace and print the reconstructed ledger."""
    audit_file = Path(audit_path) if audit_path else None
    if latest:
        audit_file = _latest_audit_file(Path(runs_dir))
        if audit_file is None:
            typer.echo("[praevisio] No audits found.")
            raise typer.Exit(code=2)
    if audit_file is None:
        typer.echo("[praevisio] audit_path is required unless --latest is used.")
        raise typer.Exit(code=2)
    manifest_path = audit_file.parent / "manifest.json"
    manifest = None
    manifest_metadata: dict = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_metadata = manifest.get("metadata") or {}
    mismatches = []
    if manifest_metadata:
        current_metadata = current_toolchain_metadata()
        mismatches = compare_toolchain(manifest_metadata, current_metadata)
    retention = manifest_metadata.get("evidence_retention")
    if retention is None:
        if manifest_metadata.get("hash_only_evidence_retention") or manifest_metadata.get(
            "hash_only_evidence"
        ):
            retention = "hash_only"
    if retention == "hash_only" and manifest:
        missing = []
        for artifact in manifest.get("artifacts", []):
            rel = artifact.get("path") or artifact.get("pointer")
            if not rel:
                continue
            if not (manifest_path.parent / rel).exists():
                missing.append(rel)
        if missing:
            typer.echo(f"[praevisio][replay] missing evidence artifact: {missing[0]}")
            raise typer.Exit(code=2)
    audit = json.loads(audit_file.read_text(encoding="utf-8"))
    result = replay_session(audit)
    if json_output:
        payload = result.to_dict_view()
        if mismatches:
            payload["determinism"] = {"toolchain_mismatches": mismatches}
        typer.echo(json.dumps(payload, indent=2))
        if strict_determinism and mismatches:
            raise typer.Exit(code=1)
        return
    if mismatches:
        typer.echo(f"[praevisio][determinism] toolchain mismatch: {', '.join(mismatches)}")
    typer.echo(f"Stop reason: {result.stop_reason}")
    typer.echo(f"Ledger: {result.ledger}")
    roots = result.roots or {}
    for rid, root in roots.items():
        k_root = root.get("k_root")
        if k_root is not None:
            typer.echo(f"Root {rid} k_root: {k_root}")
    if strict_determinism and mismatches:
        raise typer.Exit(code=1)


@app.command("show-run")
def show_run(
    run_id: str = typer.Argument(..., help="Run identifier under the runs directory."),
    runs_dir: str = typer.Option(
        ".praevisio/runs", "--runs-dir", help="Base directory for run artifacts."
    ),
) -> None:
    """Show a summary of a stored run (manifest + audit paths)."""
    run_root = Path(runs_dir) / run_id
    manifest_path = run_root / "manifest.json"
    audit_path = run_root / "audit.json"
    if not manifest_path.exists():
        typer.echo(f"[praevisio] manifest not found: {manifest_path}")
        raise typer.Exit(code=2)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    typer.echo(f"Run: {run_id}")
    metadata = manifest.get("metadata", {})
    if metadata:
        typer.echo(f"Timestamp: {metadata.get('timestamp_utc')}")
        typer.echo(f"Praevisio: {metadata.get('praevisio_version')}")
        typer.echo(f"Abductio: {metadata.get('abductio_core_version')}")
    typer.echo(f"Manifest: {manifest_path}")
    if audit_path.exists():
        typer.echo(f"Audit: {audit_path}")
    artifacts = manifest.get("artifacts", [])
    if artifacts:
        typer.echo("Artifacts:")
        for item in artifacts:
            kind = item.get("kind")
            path = item.get("path")
            sha = item.get("sha256")
            typer.echo(f"- {kind}: {path} ({sha})")


@app.command("export")
def export_audit_pack_cmd(
    run: str = typer.Option(..., "--run", help="Run identifier under the runs directory."),
    out: str = typer.Option(..., "--out", help="Path to write the audit pack bundle."),
    runs_dir: str = typer.Option(
        ".praevisio/runs", "--runs-dir", help="Base directory for run artifacts."
    ),
) -> None:
    """Export a portable audit pack bundle for offline verification."""
    run_root = Path(runs_dir) / run
    if not run_root.exists():
        typer.echo(f"[praevisio] run not found: {run_root}")
        raise typer.Exit(code=2)
    export_audit_pack(run_root, Path(out))
    typer.echo(f"[praevisio][export] wrote {out}")


@app.command("verify")
def verify_audit_pack_cmd(
    bundle: str = typer.Argument(..., help="Path to an audit pack bundle (zip)."),
    json_output: bool = typer.Option(
        False,
        "--json-output",
        "--json",
        help="Print structured JSON output instead of plain text.",
    ),
) -> None:
    """Verify an audit pack bundle (hash chain, signatures, evidence hashes)."""
    ok, error, payload = verify_audit_pack(Path(bundle))
    if json_output:
        if not payload:
            payload = {"integrity_ok": False, "error": error}
        typer.echo(json.dumps(payload, indent=2))
        if not ok:
            raise typer.Exit(code=1)
        return
    if ok:
        typer.echo("[praevisio][verify] integrity_ok")
        return
    typer.echo(f"[praevisio][verify] failed: {error}")
    raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Print Praevisio version."""
    from .. import __version__

    typer.echo(f"praevisio {__version__}")


def _latest_audit_file(runs_dir: Path) -> Path | None:
    if not runs_dir.exists():
        return None
    candidates = []
    for entry in runs_dir.iterdir():
        if not entry.is_dir():
            continue
        audit_path = entry / "audit.json"
        if audit_path.exists():
            candidates.append(audit_path)
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _write_decision(
    result,
    evaluation,
    *,
    enforcement_mode: str,
    fail_on_violation: bool,
    include_notification: bool,
) -> Path | None:
    manifest_path = result.details.get("manifest_path")
    audit_path = result.details.get("audit_path")
    run_root = None
    if manifest_path:
        run_root = Path(manifest_path).parent
    elif audit_path:
        run_root = Path(audit_path).parent
    if run_root is None:
        return None
    timestamp = None
    manifest_file = run_root / "manifest.json"
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        metadata = manifest.get("metadata") or {}
        timestamp = metadata.get("timestamp_utc")
    decision = build_decision(
        result,
        evaluation,
        enforcement_mode=enforcement_mode,
        fail_on_violation=fail_on_violation,
        timestamp_utc=timestamp,
    )
    if include_notification:
        decision = add_notification(decision, evaluation=evaluation, result=result)
    decision_path = run_root / "decision.json"
    decision_path.write_text(json.dumps(decision, indent=2), encoding="utf-8")
    return decision_path


def main() -> None:
    app()
