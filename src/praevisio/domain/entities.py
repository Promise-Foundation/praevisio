from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

from .value_objects import HookType, ExitCode, FilePattern


@dataclass(frozen=True)
class Hook:
    id: str
    name: str
    type: HookType
    command: Sequence[str]
    patterns: Sequence[FilePattern] = field(default_factory=list)
    depends_on: Sequence[str] = field(default_factory=list)
    enabled: bool = True
    file_scoped: bool = True  # whether to filter by matching files


@dataclass(frozen=True)
class HookResult:
    hook_id: str
    skipped: bool
    exit_code: ExitCode
    matched_files: List[str]


@dataclass(frozen=True)
class ValidationRule:
    id: str
    description: str


@dataclass(frozen=True)
class CommitContext:
    staged_files: List[str]
    commit_message: str = ""

