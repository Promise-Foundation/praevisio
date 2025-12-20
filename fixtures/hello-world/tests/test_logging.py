from app.src.llm_gateway import generate


def test_generate_logs_and_calls(tmp_path) -> None:
    log_path = tmp_path / "llm_log.txt"
    assert generate("hello", log_path) == "echo:hello"
    assert generate("world", log_path) == "echo:world"
    assert log_path.read_text(encoding="utf-8") == "hello\nworld\n"
