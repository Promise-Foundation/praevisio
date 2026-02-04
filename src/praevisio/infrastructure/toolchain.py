from __future__ import annotations

import platform
from typing import Any, Dict, List

try:
    from importlib import metadata as importlib_metadata  # Python 3.8+
except Exception:  # pragma: no cover - fallback
    import importlib_metadata  # type: ignore


def _package_version(name: str) -> str:
    try:
        return importlib_metadata.version(name)
    except Exception:
        return "unknown"


def _module_version(module_name: str, fallback_package: str) -> str:
    try:
        module = __import__(module_name)
        return getattr(module, "__version__", _package_version(fallback_package))
    except Exception:
        return _package_version(fallback_package)


def current_toolchain_metadata() -> Dict[str, Any]:
    return {
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "tool_versions": {
            "pytest": _package_version("pytest"),
            "semgrep": _package_version("semgrep"),
        },
        "praevisio_version": _module_version("praevisio", "praevisio"),
        "abductio_core_version": _module_version("abductio_core", "abductio-core"),
    }


def compare_toolchain(manifest_metadata: Dict[str, Any], current_metadata: Dict[str, Any]) -> List[str]:
    mismatches: List[str] = []
    for key in ("os", "python_version", "praevisio_version", "abductio_core_version"):
        recorded = manifest_metadata.get(key)
        current = current_metadata.get(key)
        if recorded and current and recorded != current:
            mismatches.append(key)
    recorded_tools = manifest_metadata.get("tool_versions") or {}
    current_tools = current_metadata.get("tool_versions") or {}
    for tool, recorded_version in recorded_tools.items():
        current_version = current_tools.get(tool)
        if recorded_version and current_version and recorded_version != current_version:
            mismatches.append(f"tool_versions.{tool}")
    return mismatches
