from __future__ import annotations

import re
from typing import Pattern

EMAIL_PATTERN: Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
PHONE_PATTERN: Pattern[str] = re.compile(
    r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)
SSN_PATTERN: Pattern[str] = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN: Pattern[str] = re.compile(
    r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
)

def _luhn_is_valid(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if not 13 <= len(digits) <= 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for idx, ch in enumerate(digits):
        d = int(ch)
        if idx % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def _redact_credit_card(match: re.Match[str]) -> str:
    candidate = match.group(0)
    if _luhn_is_valid(candidate):
        return "[REDACTED_CREDIT_CARD]"
    return candidate


def redact(text: str) -> str:
    """Redact PII from text using regex patterns."""
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    text = SSN_PATTERN.sub("[REDACTED_SSN]", text)
    text = CREDIT_CARD_PATTERN.sub(_redact_credit_card, text)
    return text
