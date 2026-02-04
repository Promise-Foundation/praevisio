from __future__ import annotations

import hmac
import os
import hashlib


def _signing_key() -> bytes:
    key = os.environ.get("PRAEVISIO_SIGNING_KEY", "dev-signing-key")
    return key.encode("utf-8")


def sign_bytes(data: bytes) -> str:
    return hmac.new(_signing_key(), data, hashlib.sha256).hexdigest()


def verify_bytes(data: bytes, signature: str) -> bool:
    expected = sign_bytes(data)
    return hmac.compare_digest(expected, signature)
