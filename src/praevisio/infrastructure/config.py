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
        promises_raw = raw.get("promises", []) or []
        promises = [str(item) for item in promises_raw] if isinstance(promises_raw, list) else []
        defaults = EvaluationConfig()
        thresholds = evaluation_raw.get("thresholds", {}) or {}
        rules_path_raw = evaluation_raw.get("semgrep_rules_path", defaults.semgrep_rules_path)
        callsite_rule_raw = evaluation_raw.get("semgrep_callsite_rule_id", defaults.semgrep_callsite_rule_id)
        violation_rule_raw = evaluation_raw.get("semgrep_violation_rule_id", defaults.semgrep_violation_rule_id)
        retention_raw = evaluation_raw.get("evidence_retention")
        hash_only = bool(evaluation_raw.get("hash_only_evidence", defaults.hash_only_evidence))
        if isinstance(retention_raw, str):
            normalized = retention_raw.strip().lower().replace("-", "_")
            if normalized == "hash_only":
                hash_only = True
        offline = bool(evaluation_raw.get("offline", defaults.offline))
        evaluation = EvaluationConfig(
            promise_id=evaluation_raw.get("promise_id", defaults.promise_id),
            threshold=float(evaluation_raw.get("threshold", defaults.threshold)),
            severity=evaluation_raw.get("severity", defaults.severity),
            pytest_args=list(evaluation_raw.get("pytest_args", defaults.pytest_args)),
            pytest_targets=list(evaluation_raw.get("pytest_targets", defaults.pytest_targets)),
            semgrep_rules_path="" if rules_path_raw is None else str(rules_path_raw),
            semgrep_callsite_rule_id="" if callsite_rule_raw is None else str(callsite_rule_raw),
            semgrep_violation_rule_id="" if violation_rule_raw is None else str(violation_rule_raw),
            thresholds={k: float(v) for k, v in thresholds.items()},
            abductio_credits=int(evaluation_raw.get("abductio_credits", defaults.abductio_credits)),
            abductio_tau=float(evaluation_raw.get("abductio_tau", defaults.abductio_tau)),
            abductio_epsilon=float(evaluation_raw.get("abductio_epsilon", defaults.abductio_epsilon)),
            abductio_gamma=float(evaluation_raw.get("abductio_gamma", defaults.abductio_gamma)),
            abductio_gamma_noa=float(
                evaluation_raw.get("abductio_gamma_noa", defaults.abductio_gamma_noa)
            ),
            abductio_gamma_und=float(
                evaluation_raw.get("abductio_gamma_und", defaults.abductio_gamma_und)
            ),
            abductio_alpha=float(evaluation_raw.get("abductio_alpha", defaults.abductio_alpha)),
            abductio_beta=float(evaluation_raw.get("abductio_beta", defaults.abductio_beta)),
            abductio_weight_cap=float(
                evaluation_raw.get(
                    "abductio_weight_cap",
                    evaluation_raw.get("abductio_W", defaults.abductio_weight_cap),
                )
            ),
            abductio_lambda_voi=float(
                evaluation_raw.get("abductio_lambda_voi", defaults.abductio_lambda_voi)
            ),
            abductio_world_mode=str(
                evaluation_raw.get("abductio_world_mode", defaults.abductio_world_mode)
            ),
            abductio_required_slots=list(
                evaluation_raw.get("abductio_required_slots", defaults.abductio_required_slots)
            ),
            run_dir=str(evaluation_raw.get("run_dir", defaults.run_dir)),
            hash_only_evidence=hash_only,
            offline=offline,
            determinism_mode=str(
                evaluation_raw.get("determinism_mode", defaults.determinism_mode)
            ),
            determinism_runs=int(
                evaluation_raw.get("determinism_runs", defaults.determinism_runs)
            ),
            determinism_seed=(
                int(evaluation_raw["determinism_seed"])
                if "determinism_seed" in evaluation_raw and evaluation_raw["determinism_seed"] is not None
                else defaults.determinism_seed
            ),
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
        return Configuration(hooks=hooks, evaluation=evaluation, promises=promises)
