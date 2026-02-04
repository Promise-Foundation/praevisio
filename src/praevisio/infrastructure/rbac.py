from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RbacAuditLog:
    entries: List[Dict[str, Any]] = field(default_factory=list)

    def record_denial(self, *, user: str, action: str, reason: str) -> None:
        self.entries.append(
            {
                "event_type": "rbac_denial",
                "user": user,
                "action": action,
                "reason": reason,
            }
        )


class EvidenceAccessService:
    def __init__(self, audit_log: RbacAuditLog) -> None:
        self._audit_log = audit_log

    def request_evidence_bundle(self, user: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        if user == "analyst":
            return {"granted": True, "bundle": artifacts}
        self._audit_log.record_denial(
            user=user, action="evidence_bundle", reason="insufficient_role"
        )
        return {"granted": False}

    def request_raw_evidence(self, user: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        if user == "analyst":
            return {"granted": True, "evidence": artifacts.get("evidence")}
        self._audit_log.record_denial(
            user=user, action="raw_evidence", reason="insufficient_role"
        )
        return {"granted": False}

    def request_evidence_excerpts(self, user: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
        if user != "counsel":
            self._audit_log.record_denial(
                user=user, action="evidence_excerpts", reason="insufficient_role"
            )
            return {"granted": False}
        excerpts = ["[REDACTED]"]
        summary = {"redactions": len(excerpts)}
        return {"granted": True, "excerpts": excerpts, "redaction_summary": summary}
