from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List

from behave import given, then

from praevisio.domain.entities import EvaluationResult
from praevisio.domain.evaluation_config import EvaluationConfig


@dataclass
class SyntheticEvaluation:
    applicable: bool = True
    threshold: float = 0.8
    tau: float = 0.7
    credence: float | None = None
    k_root: float | None = None
    violations: int = 0
    tests_skipped: bool = False
    semgrep_coverage: float = 1.0
    semgrep_error: bool = False
    test_error: bool = False
    anomalies: List[str] = field(default_factory=list)
    anomaly_actions: Dict[str, str] = field(default_factory=dict)
    evidence_refs: Dict[str, List[str]] = field(default_factory=dict)
    manifest_metadata: Dict[str, Any] | None = None
    report_roots: List[Dict[str, Any]] | None = None
    ledger_noa: float | None = None
    ledger_und: float | None = None
    residual_limit: float = 0.2
    forced_verdict: str | None = None

    def build(self) -> tuple[EvaluationResult, EvaluationConfig]:
        threshold = self.threshold
        tau = self.tau
        credence = (
            self.credence
            if self.credence is not None
            else (threshold + 0.1 if self.applicable else None)
        )
        k_root = (
            self.k_root
            if self.k_root is not None
            else (tau + 0.1 if self.applicable else None)
        )

        gates: Dict[str, bool] = {}
        if self.applicable and credence is not None and k_root is not None:
            gates = {
                "credence>=threshold": credence >= threshold,
                "k_root>=tau": k_root >= tau,
            }

        evidence_refs = dict(self.evidence_refs)
        if self.violations > 0 and not evidence_refs.get("semgrep"):
            evidence_refs["semgrep"] = ["semgrep:llm-call-must-log:1"]

        evidence = {
            "violations_found": self.violations,
            "tests_skipped": self.tests_skipped,
            "semgrep_coverage": self.semgrep_coverage,
        }

        anomalies = list(self.anomalies)
        residual_exceeds = False
        if self.residual_limit is not None:
            if (self.ledger_noa is not None and self.ledger_noa > self.residual_limit) or (
                self.ledger_und is not None and self.ledger_und > self.residual_limit
            ):
                residual_exceeds = True
                if not anomalies:
                    anomalies.append("underdetermined")

        details = {
            "gates": gates,
            "evidence": evidence,
            "evidence_refs": evidence_refs,
            "k_root": k_root,
            "applicable": self.applicable,
            "semgrep_error": "semgrep error" if self.semgrep_error else None,
            "test_error": "pytest error" if self.test_error else None,
            "anomalies": anomalies,
            "anomaly_actions": self.anomaly_actions,
        }
        if self.report_roots is not None:
            details["report"] = {"roots": self.report_roots}
        ledger: Dict[str, float] = {}
        if self.ledger_noa is not None:
            ledger["H_NOA"] = self.ledger_noa
        if self.ledger_und is not None:
            ledger["H_UND"] = self.ledger_und
        if ledger:
            details["session"] = {"ledger": ledger}

        verdict = self.forced_verdict
        if verdict is None:
            if self.semgrep_error or self.test_error:
                verdict = "error"
            elif not self.applicable:
                verdict = "n/a"
            else:
                if self.violations > 0:
                    verdict = "red"
                elif gates and (not gates["credence>=threshold"] or not gates["k_root>=tau"]):
                    verdict = "red"
                elif self.tests_skipped or self.semgrep_coverage < 0.5:
                    verdict = "red"
                elif residual_exceeds and any(
                    item in {"library_mismatch", "underdetermined"} for item in anomalies
                ):
                    verdict = "red"
                else:
                    verdict = "green"

        evaluation = EvaluationConfig(
            promise_id="llm-input-logging",
            threshold=threshold,
            abductio_tau=tau,
        )
        result = EvaluationResult(credence=credence, verdict=verdict, details=details)
        return result, evaluation


def _synthetic(context) -> SyntheticEvaluation:
    synthetic = getattr(context, "synthetic_evaluation", None)
    if synthetic is None:
        synthetic = SyntheticEvaluation()
        context.synthetic_evaluation = synthetic
    return synthetic


def _should_fail(result: EvaluationResult, evaluation: EvaluationConfig, fail_on_violation: bool) -> bool:
    if not fail_on_violation:
        return False
    if result.verdict == "error":
        return True
    if not result.details.get("applicable", True):
        return False
    if result.credence is None:
        return True
    return result.credence < evaluation.threshold


@given("an applicable promise evaluation")
def step_applicable(context) -> None:
    _synthetic(context).applicable = True


@given("credence is above the threshold")
def step_credence_above(context) -> None:
    synthetic = _synthetic(context)
    synthetic.credence = synthetic.threshold + 0.1


@given("credence is below the threshold")
def step_credence_below(context) -> None:
    synthetic = _synthetic(context)
    synthetic.credence = synthetic.threshold - 0.1


@given("k_root is above tau")
def step_kroot_above(context) -> None:
    synthetic = _synthetic(context)
    synthetic.k_root = synthetic.tau + 0.1


@given("k_root is below tau")
def step_kroot_below(context) -> None:
    synthetic = _synthetic(context)
    synthetic.k_root = synthetic.tau - 0.1


@given("semgrep fails to run or returns an error")
def step_semgrep_error(context) -> None:
    synthetic = _synthetic(context)
    synthetic.semgrep_error = True


@given("the promise is not applicable to this repository")
def step_not_applicable(context) -> None:
    synthetic = _synthetic(context)
    synthetic.applicable = False
    synthetic.credence = None
    synthetic.k_root = None


@given("all required slots have p above their minima")
def step_required_slots_ok(context) -> None:
    synthetic = _synthetic(context)
    synthetic.credence = synthetic.threshold + 0.1
    synthetic.k_root = synthetic.tau + 0.1


@given("the root credence is above threshold")
def step_root_credence_above(context) -> None:
    synthetic = _synthetic(context)
    synthetic.credence = synthetic.threshold + 0.1


@given("residual mass assigned to NOA is below the policy limit")
def step_noa_below_limit(context) -> None:
    synthetic = _synthetic(context)
    synthetic.ledger_noa = 0.05
    synthetic.residual_limit = 0.2


@given('semgrep finds at least 1 violation of "llm-call-must-log"')
def step_semgrep_violation(context) -> None:
    synthetic = _synthetic(context)
    synthetic.violations = 1
    synthetic.evidence_refs["semgrep"] = ["semgrep:llm-call-must-log:1"]


@given("there are no explicit violations")
def step_no_violations(context) -> None:
    _synthetic(context).violations = 0


@given("tests are skipped and coverage is low")
def step_tests_skipped(context) -> None:
    synthetic = _synthetic(context)
    synthetic.tests_skipped = True
    synthetic.semgrep_coverage = 0.4


@given("applicability fit is low across all roots")
def step_low_fit(context) -> None:
    synthetic = _synthetic(context)
    synthetic.anomalies = ["library_mismatch"]
    min_residual = getattr(context, "min_residual_mass", None)
    if min_residual is not None and synthetic.ledger_noa is None:
        synthetic.ledger_noa = float(min_residual) + 0.1


@given("residual mass exceeds the policy limit")
def step_residual_exceeds(context) -> None:
    synthetic = _synthetic(context)
    synthetic.ledger_noa = 0.6
    synthetic.residual_limit = 0.2


@then('the promise verdict should be "{expected}"')
def step_promise_verdict(context, expected: str) -> None:
    assert context.result.verdict == expected, context.result


@then('the overall verdict should be "{expected}"')
def step_overall_verdict(context, expected: str) -> None:
    report_path = getattr(context, "report_path", None)
    if report_path and Path(report_path).exists():
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
        overall = report.get("overall_verdict")
        assert overall == expected, overall
        return
    decision_verdict = context.decision.get("overall_verdict")
    if expected == "allow":
        assert decision_verdict in {"green", "n/a"}, decision_verdict
    elif expected == "block":
        assert decision_verdict in {"red", "error"}, decision_verdict
    else:
        assert decision_verdict == expected, decision_verdict


@then("the overall decision should not be blocked by this promise")
def step_not_blocked(context) -> None:
    decision_verdict = context.decision.get("overall_verdict")
    assert decision_verdict in {"green", "n/a"}, decision_verdict


@then('the decision should include a reason code "{code}"')
def step_reason_code(context, code: str) -> None:
    reasons = context.decision.get("promise_results", [{}])[0].get("reason_codes", [])
    assert code in reasons, reasons


@then("the CI gate should fail when fail-on-violation is enabled")
def step_ci_gate_fail(context) -> None:
    assert _should_fail(context.result, context.evaluation, True)


@then('the decision should include "mechanisms" listing which gates were satisfied')
def step_mechanisms(context) -> None:
    mechanisms = context.decision.get("mechanisms") or []
    assert "credence_gate_pass" in mechanisms, mechanisms
    assert "support_gate_pass" in mechanisms, mechanisms


@then('the decision should record "residuals" including "NOA_mass"')
def step_residuals(context) -> None:
    residuals = context.decision.get("residuals") or {}
    assert "NOA_mass" in residuals, residuals


@then('the decision should include a mechanism "{mechanism}"')
def step_decision_mechanism(context, mechanism: str) -> None:
    mechanisms = context.decision.get("mechanisms") or []
    assert mechanism in mechanisms, mechanisms


@then("it should list evidence references for the violating finding")
def step_violation_refs(context) -> None:
    promise = context.decision.get("promise_results", [{}])[0]
    refs = promise.get("violation_evidence_refs") or []
    assert refs, promise


@then("it should include recommended next actions")
def step_next_actions(context) -> None:
    actions = context.decision.get("next_actions") or []
    assert actions, actions
    for action in actions:
        assert "title" in action
        assert "rationale" in action
        assert "expected_impact" in action


@then('the decision should include anomaly "{first}" or "{second}"')
def step_anomaly(context, first: str, second: str) -> None:
    anomalies = context.decision.get("anomalies") or []
    assert any(item in anomalies for item in (first, second)), anomalies


@then('the verdict should be "red" or "yellow" according to policy')
def step_red_or_yellow(context) -> None:
    assert context.result.verdict in {"red", "yellow"}, context.result.verdict
