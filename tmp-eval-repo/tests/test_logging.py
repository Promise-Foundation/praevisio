from __future__ import annotations

from app.src.llm_client import generate


def test_generate_logs_and_calls() -> None:
    result = generate("hello")
    assert result == "echo:hello"
