from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from behave import given, when, then

from praevisio.application.engine import PraevisioEngine
from praevisio.domain.config import Configuration
from praevisio.domain.evaluation_config import EvaluationConfig
from praevisio.domain.entities import EvaluationResult
from praevisio.domain.ports import ConfigLoader, FileSystemService


class DummyConfigLoader(ConfigLoader):
    def load(self, path: str) -> Configuration:
        return Configuration()


class DummyFileSystem(FileSystemService):
    def read_text(self, path: str) -> str:
        return ""

    def write_text(self, path: str, content: str) -> None:
        return None


@dataclass
class FakeEvaluationService:
    result: EvaluationResult

    def evaluate_path(self, path: str, *args, **kwargs) -> EvaluationResult:
        return self.result


@given("a high-severity red evaluation result")
def step_high_severity_red(context) -> None:
    evaluation = EvaluationConfig(
        promise_id="llm-input-logging",
        threshold=0.95,
        severity="high",
    )
    result = EvaluationResult(
        credence=0.5,
        verdict="red",
        details={"applicable": True},
    )
    context.evaluation = evaluation
    context.engine = PraevisioEngine(
        config_loader=DummyConfigLoader(),
        fs=DummyFileSystem(),
        evaluation_service=FakeEvaluationService(result),
    )
    context.now = datetime(2026, 2, 4, tzinfo=timezone.utc)


@given('an override expires at "{expires_at}"')
def step_override_expiry(context, expires_at: str) -> None:
    context.override_payload = {
        "decision_sha256": "deadbeef",
        "approved_by": "alice",
        "expires_at": expires_at,
        "compensating_controls": [],
        "signature": "sig",
    }


@given("the override includes compensating controls")
def step_override_with_controls(context) -> None:
    context.override_payload["compensating_controls"] = ["extra_monitoring"]


@given("the override lacks compensating controls")
def step_override_without_controls(context) -> None:
    context.override_payload["compensating_controls"] = []


@when("I apply the override to the CI gate")
def step_apply_override(context) -> None:
    gate = context.engine.ci_gate(
        path=".",
        evaluation=context.evaluation,
        severity=context.evaluation.severity,
        fail_on_violation=True,
        override=context.override_payload,
        now=context.now,
    )
    context.gate_result = gate


@then("the gate should remain blocked")
def step_gate_blocked(context) -> None:
    assert context.gate_result.should_fail is True


@then("the override should unblock the gate")
def step_override_unblocks(context) -> None:
    assert context.gate_result.should_fail is False
    assert context.gate_result.report_entry.get("override_applied") is True
