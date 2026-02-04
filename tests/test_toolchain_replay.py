from __future__ import annotations

import json

from typer.testing import CliRunner

from praevisio.presentation import cli


class FakeReplayResult:
    def __init__(self) -> None:
        self.stop_reason = "done"
        self.ledger = {"promise": 0.9}
        self.roots = {"promise": {"k_root": 0.9}}

    def to_dict_view(self):
        return {
            "stop_reason": self.stop_reason,
            "ledger": self.ledger,
            "roots": self.roots,
        }


def test_replay_warns_on_toolchain_mismatch(monkeypatch, tmp_path) -> None:
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps({"events": []}), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "python_version": "0.0.0",
                    "tool_versions": {"pytest": "0.0.0"},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "replay_session", lambda audit: FakeReplayResult())
    runner = CliRunner()
    result = runner.invoke(cli.app, ["replay-audit", str(audit_path)])
    assert result.exit_code == 0
    assert "toolchain mismatch" in result.output


def test_replay_strict_fails_on_toolchain_mismatch(monkeypatch, tmp_path) -> None:
    audit_path = tmp_path / "audit.json"
    audit_path.write_text(json.dumps({"events": []}), encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "metadata": {
                    "python_version": "0.0.0",
                    "tool_versions": {"pytest": "0.0.0"},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "replay_session", lambda audit: FakeReplayResult())
    runner = CliRunner()
    result = runner.invoke(cli.app, ["replay-audit", str(audit_path), "--strict-determinism"])
    assert result.exit_code == 1
    assert "toolchain mismatch" in result.output
