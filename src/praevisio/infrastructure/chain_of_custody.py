from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class ChainOfCustodyLog:
    entries: List[Dict[str, Any]] = field(default_factory=list)

    def record_access(
        self,
        evidence_id: str,
        *,
        actor: str,
        purpose: str,
        timestamp: str | None = None,
    ) -> Dict[str, Any]:
        entry = {
            "event_type": "evidence_access",
            "evidence_id": evidence_id,
            "actor": actor,
            "purpose": purpose,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        }
        self.entries.append(entry)
        return entry

    def record_transform(
        self,
        evidence_id: str,
        *,
        transform: str,
        input_hash: str,
        output_hash: str,
        tool_version: str,
        actor: str,
        purpose: str,
        timestamp: str | None = None,
    ) -> Dict[str, Any]:
        entry = {
            "event_type": "evidence_transform",
            "evidence_id": evidence_id,
            "transform": transform,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "tool_version": tool_version,
            "actor": actor,
            "purpose": purpose,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        }
        self.entries.append(entry)
        return entry
