from __future__ import annotations

from pathlib import Path


def log(prompt: str, log_path: Path) -> None:
    with log_path.open("a", encoding="utf-8") as f:
        f.write(prompt + "\n")


def call_llm(prompt: str) -> str:
    return f"echo:{prompt}"


def generate(prompt: str, log_path: Path) -> str:
    log(prompt, log_path)
    return call_llm(prompt)
