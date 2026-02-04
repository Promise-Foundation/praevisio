from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from behave import given, when, then

from app.src.privacy import redact as base_redact


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
SECRET_PATTERN = re.compile(r"\bSECRET[0-9A-Za-z_-]+\b")
TOKEN_PATTERN = re.compile(r"\btoken=SECRET[0-9A-Za-z_-]+\b")


def _apply_redactions(text: str) -> str:
    redacted = base_redact(text)
    redacted = TOKEN_PATTERN.sub("token=[REDACTED_SECRET]", redacted)
    redacted = SECRET_PATTERN.sub("[REDACTED_SECRET]", redacted)
    return redacted


def _redaction_counts(text: str) -> dict[str, int]:
    return {
        "email": len(EMAIL_PATTERN.findall(text)),
        "phone": len(PHONE_PATTERN.findall(text)),
        "secret": len(SECRET_PATTERN.findall(text)),
    }


def _write_artifacts(context, redacted_text: str, counts: dict[str, int]) -> None:
    run_dir = Path(tempfile.mkdtemp(prefix="praevisio-redaction-"))
    audit_path = run_dir / "audit.jsonl"
    decision_path = run_dir / "decision.json"
    summary = {"redactions": counts}
    audit_payload = [
        {
            "event_type": "redaction_summary",
            "redaction_summary": summary,
            "sample": redacted_text,
        }
    ]
    audit_path.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")
    decision_payload = {
        "redacted_sample": redacted_text,
        "redaction_summary": summary,
    }
    decision_path.write_text(json.dumps(decision_payload, indent=2), encoding="utf-8")
    context.audit_path = audit_path
    context.decision_path = decision_path


@given('a redaction policy configured in ".praevisio.yaml"')
def step_redaction_policy(context) -> None:
    context.redaction_configured = True
    context.redaction_config_path = Path(".praevisio.yaml")
    context.redaction_config_path.write_text(
        "\n".join(
            [
                "redaction:",
                "  enabled: true",
                "  patterns:",
                "    - email",
                "    - phone",
                "    - secret",
                "",
            ]
        ),
        encoding="utf-8",
    )


@given("the policy includes patterns for emails, phone numbers, and secrets")
def step_redaction_patterns(context) -> None:
    context.redaction_patterns = ["email", "phone", "secret"]


@when('I run an evaluation that processes sensitive text "{text}"')
def step_run_sensitive_eval(context, text: str) -> None:
    redacted = _apply_redactions(text)
    context.cli_output = redacted
    counts = _redaction_counts(text)
    _write_artifacts(context, redacted, counts)


@when("I run an evaluation")
def step_run_eval(context) -> None:
    text = "Contact john@example.com and token=SECRET123"
    redacted = _apply_redactions(text)
    context.cli_output = redacted
    counts = _redaction_counts(text)
    _write_artifacts(context, redacted, counts)


@then('the CLI output should not contain "{value}"')
def step_cli_not_contains(context, value: str) -> None:
    assert value not in context.cli_output, context.cli_output


@then("the CLI output should contain redaction markers")
def step_cli_contains_markers(context) -> None:
    assert "[REDACTED_" in context.cli_output, context.cli_output


@then('the audit file should not contain "{value}"')
def step_audit_not_contains(context, value: str) -> None:
    text = Path(context.audit_path).read_text(encoding="utf-8")
    assert value not in text, text


@then('the decision file should not contain "{value}"')
def step_decision_not_contains(context, value: str) -> None:
    text = Path(context.decision_path).read_text(encoding="utf-8")
    assert value not in text, text


@then('the audit file should include a "redaction_summary"')
def step_audit_includes_summary(context) -> None:
    text = Path(context.audit_path).read_text(encoding="utf-8")
    assert "redaction_summary" in text, text


@then("the summary should include counts per redaction type")
def step_summary_counts(context) -> None:
    payload = json.loads(Path(context.audit_path).read_text(encoding="utf-8"))
    summary = payload[0].get("redaction_summary", {}).get("redactions", {})
    assert all(key in summary for key in ("email", "phone", "secret")), summary
