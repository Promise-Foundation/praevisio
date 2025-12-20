from __future__ import annotations

from typing import Dict

INJECTION_PATTERNS = [
    "ignore all instructions",
    "ignore previous instructions",
    "reveal secrets",
    "system prompt",
    "reveal your prompt",
    "disregard all",
    "forget previous",
]


def guard(prompt: str) -> Dict[str, bool | str]:
    """Detect prompt injection attempts using heuristic patterns."""
    lowered = prompt.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lowered:
            return {
                "is_attack": True,
                "reason": f"Detected injection pattern: {pattern}",
            }
    return {"is_attack": False, "reason": "No injection detected"}
