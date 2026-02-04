from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Tuple


def _extract_events(audit: Any) -> List[Dict[str, Any]]:
    if isinstance(audit, dict) and isinstance(audit.get("events"), list):
        return audit["events"]
    if isinstance(audit, list):
        return audit
    return []


def _canonical_event(event_type: str | None, payload: Dict[str, Any]) -> str:
    return json.dumps(
        {"event_type": event_type, "payload": payload},
        sort_keys=True,
    )


def chain_audit_log(audit: Any) -> Any:
    events = _extract_events(audit)
    prev_hash = "GENESIS"
    for event in events:
        payload = dict(event.get("payload") or {})
        payload["prev_hash"] = prev_hash
        entry_hash = hashlib.sha256(
            _canonical_event(event.get("event_type"), payload).encode("utf-8")
        ).hexdigest()
        payload["entry_hash"] = entry_hash
        event["payload"] = payload
        prev_hash = entry_hash
    return audit


def validate_audit_log(audit: Any) -> Tuple[bool, str]:
    events = _extract_events(audit)
    prev_hash = "GENESIS"
    for event in events:
        payload = dict(event.get("payload") or {})
        if "prev_hash" not in payload or "entry_hash" not in payload:
            return False, "hash chain missing entry"
        if payload["prev_hash"] != prev_hash:
            return False, "hash chain mismatch (missing entry)"
        entry_hash = payload.pop("entry_hash")
        expected = hashlib.sha256(
            _canonical_event(event.get("event_type"), payload).encode("utf-8")
        ).hexdigest()
        if entry_hash != expected:
            return False, "hash chain mismatch"
        prev_hash = entry_hash
    return True, ""
