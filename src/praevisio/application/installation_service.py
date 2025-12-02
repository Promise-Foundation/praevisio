from __future__ import annotations

from ..domain.ports import FileSystemService


DEFAULT_CONFIG = """
hooks:
  - id: example-lint
    name: Example Lint
    type: pre-commit
    command: ["echo", "lint"]
    patterns: ["**/*.py"]
""".lstrip()


class InstallationService:
    def __init__(self, fs: FileSystemService, config_path: str = ".praevisio.yaml") -> None:
        self._fs = fs
        self._path = config_path

    def install(self) -> str:
        self._fs.write_text(self._path, DEFAULT_CONFIG)
        return self._path

