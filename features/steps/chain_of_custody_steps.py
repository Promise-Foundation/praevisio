from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from behave import given, when, then

from praevisio.infrastructure.chain_of_custody import ChainOfCustodyLog
from praevisio.infrastructure.evidence_store import EvidenceStore


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@given("an evidence store with at least one document")
def step_evidence_store(context) -> None:
    base_dir = Path(tempfile.mkdtemp(prefix="praevisio-custody-"))
    context.evidence_store = EvidenceStore(base_dir)
    context.evidence_id = "E123"
    context.evidence_path = "evidence/E123.txt"
    context.evidence_store.write_text(
        context.evidence_path, "sample content", kind="document"
    )


@given("chain-of-custody logging is enabled")
def step_enable_custody(context) -> None:
    context.custody_log = ChainOfCustodyLog()
    context.evidence_store.enable_chain_of_custody(context.custody_log)


@when('a component reads evidence "E123"')
def step_read_evidence(context) -> None:
    context.evidence_store.read_text(
        context.evidence_path,
        evidence_id=context.evidence_id,
        actor="component",
        purpose="evaluation",
    )


@then('the audit should include an "evidence_access" entry for "E123"')
def step_assert_access_entry(context) -> None:
    entries = context.custody_log.entries
    assert any(
        e.get("event_type") == "evidence_access" and e.get("evidence_id") == "E123"
        for e in entries
    ), entries


@then('the entry should include "actor", "timestamp", and "purpose"')
def step_assert_access_fields(context) -> None:
    entry = next(
        e
        for e in context.custody_log.entries
        if e.get("event_type") == "evidence_access" and e.get("evidence_id") == "E123"
    )
    assert entry.get("actor")
    assert entry.get("timestamp")
    assert entry.get("purpose")


@when('I run a transformation "ocr" on evidence "E123"')
def step_transform_evidence(context) -> None:
    original = "sample content"
    transformed = original.upper()
    context.custody_log.record_transform(
        context.evidence_id,
        transform="ocr",
        input_hash=_sha256(original),
        output_hash=_sha256(transformed),
        tool_version="ocr-1.0",
        actor="component",
        purpose="ingest",
    )


@then('the audit should include an "evidence_transform" entry')
def step_assert_transform_entry(context) -> None:
    entries = context.custody_log.entries
    assert any(e.get("event_type") == "evidence_transform" for e in entries), entries


@then('it should include "input_hash" and "output_hash"')
def step_assert_transform_hashes(context) -> None:
    entry = next(e for e in context.custody_log.entries if e.get("event_type") == "evidence_transform")
    assert entry.get("input_hash")
    assert entry.get("output_hash")


@then("it should include the transformation tool version")
def step_assert_transform_version(context) -> None:
    entry = next(e for e in context.custody_log.entries if e.get("event_type") == "evidence_transform")
    assert entry.get("tool_version")
