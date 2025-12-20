from __future__ import annotations

from typing import List

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    yaml = None

from ..domain.config import Configuration
from ..domain.evaluation_config import EvaluationConfig
from ..domain.entities import Hook
from ..domain.ports import ConfigLoader
from ..domain.value_objects import HookType, FilePattern


class InMemoryConfigLoader(ConfigLoader):
    """Return a pre-built Configuration (useful for tests)."""
    def __init__(self, config: Configuration) -> None:
        self._config = config

    def load(self, path: str) -> Configuration:  # path ignored
        return self._config


class YamlConfigLoader(ConfigLoader):
    """Load Configuration from a YAML file on disk."""

    def load(self, path: str) -> Configuration:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML configuration")
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        evaluation_raw = raw.get("evaluation", {}) or {}
        defaults = EvaluationConfig()
        thresholds = evaluation_raw.get("thresholds", {}) or {}
        evaluation = EvaluationConfig(
            promise_id=evaluation_raw.get("promise_id", defaults.promise_id),
            threshold=float(evaluation_raw.get("threshold", defaults.threshold)),
            pytest_args=list(evaluation_raw.get("pytest_args", defaults.pytest_args)),
            pytest_targets=list(evaluation_raw.get("pytest_targets", defaults.pytest_targets)),
            semgrep_rules_path=str(
                evaluation_raw.get("semgrep_rules_path", defaults.semgrep_rules_path)
            ),
            thresholds={k: float(v) for k, v in thresholds.items()},
        )
        hooks = []
        for item in raw.get("hooks", []) or []:
            patterns = [FilePattern(p) for p in item.get("patterns", []) or []]
            cmd = item.get("command", []) or []
            hook = Hook(
                id=item["id"],
                name=item.get("name", item["id"]),
                type=HookType(item.get("type", "pre-commit")),
                command=cmd,
                patterns=patterns,
                depends_on=item.get("depends_on", []) or [],
                enabled=bool(item.get("enabled", True)),
                file_scoped=bool(item.get("file_scoped", True)),
            )
            hooks.append(hook)
        return Configuration(hooks=hooks, evaluation=evaluation)
