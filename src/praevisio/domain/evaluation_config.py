from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class EvaluationConfig:
    promise_id: str = "default-promise"
    threshold: float = 0.95
    pytest_args: List[str] = field(default_factory=lambda: ["-q", "--disable-warnings"])
    pytest_targets: List[str] = field(default_factory=list)
    semgrep_rules_path: str = "governance/evidence/semgrep_rules.yaml"
    thresholds: Dict[str, float] = field(default_factory=dict)
