from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass(frozen=True)
class OverrideArtifact:
    decision_sha256: str
    approved_by: str
    expires_at: datetime
    compensating_controls: list[str] = field(default_factory=list)
    signature: str | None = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "OverrideArtifact":
        expires_raw = payload.get("expires_at")
        if not isinstance(expires_raw, str):
            raise ValueError("override.expires_at is required")
        expires_at = _parse_iso_datetime(expires_raw)
        return cls(
            decision_sha256=str(payload.get("decision_sha256", "")),
            approved_by=str(payload.get("approved_by", "")),
            expires_at=expires_at,
            compensating_controls=list(payload.get("compensating_controls", []) or []),
            signature=payload.get("signature"),
        )

    def is_expired(self, now: datetime | None = None) -> bool:
        check_time = now or datetime.now(timezone.utc)
        return self.expires_at <= check_time


def parse_override(payload: OverrideArtifact | Dict[str, Any]) -> OverrideArtifact | None:
    if isinstance(payload, OverrideArtifact):
        return payload
    if isinstance(payload, dict):
        try:
            return OverrideArtifact.from_dict(payload)
        except Exception:
            return None
    return None


def _parse_iso_datetime(value: str) -> datetime:
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception as exc:
        raise ValueError(f"Invalid ISO datetime: {value}") from exc
