from __future__ import annotations

from typing import List

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional at runtime
    yaml = None

from ..domain.config import Configuration
from ..domain.entities import Hook
from ..domain.ports import ConfigLoader
from ..domain.value_objects import HookType, FilePattern


class InMemoryConfigLoader(ConfigLoader):
    def __init__(self, config: Configuration) -> None:
        self._config = config

    def load(self, path: str) -> Configuration:  # path ignored
        return self._config


class YamlConfigLoader(ConfigLoader):
    def load(self, path: str) -> Configuration:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML configuration")
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
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
        return Configuration(hooks=hooks)

