from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List

from ..domain.entities import StaticAnalysisResult, StaticFinding
from ..domain.ports import StaticAnalyzer


class SemgrepStaticAnalyzer(StaticAnalyzer):
    """StaticAnalyzer implementation using Semgrep.

    Expects a Semgrep rules file at governance/evidence/semgrep_rules.yaml
    relative to the directory where Praevisio is executed (i.e., the target
    project, such as praevisio-test).
    """

    def __init__(self, rules_path: Path | None = None) -> None:
        self._rules_path = rules_path or Path("governance/evidence/semgrep_rules.yaml")

    def analyze(self, path: str) -> StaticAnalysisResult:
        # Ensure rules file exists in the target project
        root = Path(path)
        rules_path = self._rules_path
        if not rules_path.is_absolute():
            rules_path = root / rules_path
        if not rules_path.exists():
            # Fail soft: if no rules, treat as "no static evidence"
            return StaticAnalysisResult(
                total_llm_calls=0, violations=0, coverage=1.0, findings=[]
            )

        # First: run Semgrep with JSON output using our governance rules
        result = subprocess.run(
            ["semgrep", "--config", str(rules_path), "--json", path],
            capture_output=True,
            text=True,
        )

        if result.returncode >= 2:
            raise RuntimeError(f"Semgrep failed: {result.stderr}")

        try:
            output = json.loads(result.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Could not parse Semgrep output: {exc}") from exc

        findings = output.get("results", [])

        # Filter for our specific rule; other rules may also exist
        llm_violations = [
            f for f in findings if f.get("check_id") == "llm-call-must-log"
        ]

        # Second: count total call_llm invocations separately
        count_result = subprocess.run(
            ["semgrep", "--pattern", "def call_llm($Y):", "--lang", "python", "--json", path],
            capture_output=True,
            text=True,
        )

        total_calls = 0
        if count_result.returncode < 2 and count_result.stdout.strip():
            try:
                count_output = json.loads(count_result.stdout)
                total_calls = len(count_output.get("results", []))
            except json.JSONDecodeError:
                total_calls = len(llm_violations)

        num_violations = len(llm_violations)

        if total_calls == 0:
            # Fallback: simple text scan in case Semgrep cannot count
            total_calls = sum(
                (p.read_text(encoding="utf-8").count("def call_llm("))
                for p in Path(path).rglob("*.py")
            )

        if total_calls == 0:
            # No LLM calls: treat as neutral but avoid division by zero
            coverage = 1.0
        else:
            coverage = (total_calls - num_violations) / total_calls

        findings_struct: List[StaticFinding] = []
        for f in llm_violations:
            path_str = f.get("path", "")
            start = f.get("start") or {}
            line = start.get("line")
            code = (f.get("extra") or {}).get("lines", "")
            findings_struct.append(StaticFinding(file=path_str, line=line, code=code))

        return StaticAnalysisResult(
            total_llm_calls=total_calls,
            violations=num_violations,
            coverage=coverage,
            findings=findings_struct,
        )
