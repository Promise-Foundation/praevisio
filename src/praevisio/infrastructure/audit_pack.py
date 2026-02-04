from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Tuple

from .audit_chain import validate_audit_log
from .report_signing import verify_bytes


def _extract_events(audit: Any) -> List[Dict[str, Any]]:
    if isinstance(audit, dict) and isinstance(audit.get("events"), list):
        return audit["events"]
    if isinstance(audit, list):
        return audit
    return []


def _audit_to_jsonl(audit: Any) -> str:
    events = _extract_events(audit)
    lines = [json.dumps(event, sort_keys=True) for event in events]
    return "\n".join(lines) + ("\n" if lines else "")


def export_audit_pack(run_root: Path, out_path: Path) -> None:
    manifest_path = run_root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts", [])

    audit_path = run_root / "audit.json"
    audit_payload = None
    if audit_path.exists():
        audit_payload = json.loads(audit_path.read_text(encoding="utf-8"))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(manifest_path, arcname="manifest.json")
        if audit_payload is not None:
            zf.writestr("audit.jsonl", _audit_to_jsonl(audit_payload))
        for artifact in artifacts:
            rel = artifact.get("path")
            if not rel:
                continue
            path = run_root / rel
            if path.exists():
                zf.write(path, arcname=str(rel))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_audit_pack(bundle_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
    with TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        with zipfile.ZipFile(bundle_path, "r") as zf:
            zf.extractall(tmp_root)

        manifest_path = tmp_root / "manifest.json"
        if not manifest_path.exists():
            return False, "manifest missing", {}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifacts = manifest.get("artifacts", [])

        audit_payload = None
        audit_jsonl_path = tmp_root / "audit.jsonl"
        audit_json_path = tmp_root / "audit.json"
        if audit_jsonl_path.exists():
            events = []
            for line in audit_jsonl_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    events.append(json.loads(line))
            audit_payload = {"events": events}
        elif audit_json_path.exists():
            audit_payload = json.loads(audit_json_path.read_text(encoding="utf-8"))

        if audit_payload is not None:
            ok, error = validate_audit_log(audit_payload)
            if not ok:
                return False, error or "hash chain invalid", {}

        report_path = tmp_root / "report.json"
        sig_path = tmp_root / "report.sig"
        if report_path.exists() and sig_path.exists():
            report_bytes = report_path.read_bytes()
            sig = sig_path.read_text(encoding="utf-8")
            if not verify_bytes(report_bytes, sig):
                return False, "signature verification failed", {}
        else:
            return False, "signature missing", {}

        for artifact in artifacts:
            rel = artifact.get("path")
            expected = artifact.get("sha256")
            if not rel or not expected:
                continue
            path = tmp_root / rel
            if not path.exists():
                return False, f"missing artifact: {rel}", {}
            actual = _sha256_bytes(path.read_bytes())
            if actual != expected:
                return False, f"hash mismatch for {rel}", {}

        return True, "", {"integrity_ok": True}
