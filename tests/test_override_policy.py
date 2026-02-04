from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from praevisio.application.engine import PraevisioEngine
from praevisio.domain.config import Configuration
from praevisio.domain.entities import EvaluationResult
from praevisio.domain.evaluation_config import EvaluationConfig
from praevisio.infrastructure.config import InMemoryConfigLoader
from praevisio.infrastructure.filesystem import LocalFileSystemService


@dataclass
class FakeEvaluationService:
    result: EvaluationResult

    def evaluate_path(self, path: str, config: EvaluationConfig) -> EvaluationResult:
        return self.result


def test_expired_override_cannot_unblock(tmp_path) -> None:
    evaluation = EvaluationConfig(promise_id="promise", threshold=0.9)
    result = EvaluationResult(
        credence=0.1,
        verdict="red",
        details={"applicable": True},
    )
    engine = PraevisioEngine(
        config_loader=InMemoryConfigLoader(Configuration()),
        fs=LocalFileSystemService(),
        evaluation_service=FakeEvaluationService(result),
    )
    override = {
        "decision_sha256": "deadbeef",
        "approved_by": "security",
        "expires_at": "2020-01-01T00:00:00Z",
    }
    gate = engine.ci_gate(
        str(tmp_path),
        evaluation,
        fail_on_violation=True,
        override=override,
        now=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert gate.should_fail is True
