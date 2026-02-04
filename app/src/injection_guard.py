from __future__ import annotations

import re
from typing import Dict, List, Tuple

INJECTION_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bignore (all|previous|prior) instructions\b"), "ignore all instructions"),
    (re.compile(r"\bdisregard (all|previous|prior) instructions\b"), "disregard instructions"),
    (re.compile(r"\bforget (all|previous|prior) instructions\b"), "forget instructions"),
    (re.compile(r"\breveal (secrets|system prompt|your prompt)\b"), "reveal prompt"),
    (re.compile(r"\bbegin system prompt\b"), "system prompt"),
    (re.compile(r"\bsystem prompt\b"), "system prompt"),
    (re.compile(r"\bdeveloper message\b"), "developer message"),
    (re.compile(r"\byou are chatgpt\b"), "role impersonation"),
    (re.compile(r"\brole\s*:\s*(system|developer)\b"), "role injection"),
]


def _normalize(prompt: str) -> str:
    lowered = prompt.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(normalized.split())


def guard(prompt: str) -> Dict[str, bool | str]:
    """Detect prompt injection attempts using heuristic patterns."""
    normalized = _normalize(prompt)
    for pattern, reason in INJECTION_PATTERNS:
        if pattern.search(normalized):
            return {
                "is_attack": True,
                "reason": f"Detected injection pattern: {reason}",
            }
    return {"is_attack": False, "reason": "No injection detected"}
