from __future__ import annotations

from ..domain.config import Configuration
from ..domain.ports import ConfigLoader, FileSystemService


class ConfigurationService:
    def __init__(self, loader: ConfigLoader, fs: FileSystemService, config_path: str = ".praevisio.yaml") -> None:
        self._loader = loader
        self._fs = fs
        self._path = config_path

    def load(self) -> Configuration:
        # Future: merge defaults here
        return self._loader.load(self._path)

