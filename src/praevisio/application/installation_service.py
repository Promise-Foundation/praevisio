from __future__ import annotations

from ..domain.ports import FileSystemService


DEFAULT_CONFIG = """
evaluation:
  promise_id: example-promise
  threshold: 0.95
  pytest_targets: []
  semgrep_rules_path: governance/evidence/semgrep_rules.yaml
  thresholds:
    high: 0.95
hooks:
  - id: example-lint
    name: Example Lint
    type: pre-commit
    command: ["echo", "lint"]
    patterns: ["**/*.py"]
""".lstrip()


class InstallationService:
    """Install a default .praevisio.yaml configuration file.

    Parameters
    - fs: file system adapter used to write the file
    - config_path: target path for the configuration file
    """
    def __init__(self, fs: FileSystemService, config_path: str = ".praevisio.yaml") -> None:
        self._fs = fs
        self._path = config_path

    def install(self) -> str:
        self._fs.write_text(self._path, DEFAULT_CONFIG)
        return self._path
