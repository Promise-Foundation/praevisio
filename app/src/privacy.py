from __future__ import annotations

import re
from typing import Pattern

EMAIL_PATTERN: Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)
PHONE_PATTERN: Pattern[str] = re.compile(
    r"\b(\+?1[-.]?)?(\(?\d{3}\)?[-.]?)?\d{3}[-.]?\d{4}\b"
)
SSN_PATTERN: Pattern[str] = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN: Pattern[str] = re.compile(
    r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
)


def redact(text: str) -> str:
    """Redact PII from text using regex patterns."""
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    text = SSN_PATTERN.sub("[REDACTED_SSN]", text)
    text = CREDIT_CARD_PATTERN.sub("[REDACTED_CREDIT_CARD]", text)
    return text
