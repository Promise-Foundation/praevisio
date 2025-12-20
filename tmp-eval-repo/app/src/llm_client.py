from __future__ import annotations


def log(prompt: str) -> None:
    with open("/tmp/llm_log.txt", "a", encoding="utf-8") as f:
        f.write(prompt + "\n")


def call_llm(prompt: str) -> str:
    return f"echo:{prompt}"


def generate(prompt: str) -> str:
    # intentionally missing log(prompt)
    return call_llm(prompt)
