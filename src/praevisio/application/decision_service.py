from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from ..domain.entities import EvaluationResult
from ..domain.evaluation_config import EvaluationConfig


def build_decision(
    result: EvaluationResult,
    evaluation: EvaluationConfig,
    *,
    enforcement_mode: str,
    fail_on_violation: bool,
    timestamp_utc: str | None = None,
) -> Dict[str, Any]:
    policy = {
        "threshold": evaluation.threshold,
        "thresholds": dict(evaluation.thresholds),
        "severity": evaluation.severity,
        "tau": evaluation.abductio_tau,
        "enforcement": {
            "mode": enforcement_mode,
            "fail_on_violation": fail_on_violation,
        },
    }
    promise_results = [
        _promise_result(result, evaluation)
    ]
    overall = _overall_verdict(promise_results)
    mechanisms = _mechanisms(result, evaluation)
    residuals = _residuals(result)
    anomalies = list(result.details.get("anomalies") or [])
    next_actions = _next_actions(promise_results[0], result)
    decision = {
        "schema_version": "1.0",
        "run_id": result.details.get("run_id"),
        "timestamp_utc": timestamp_utc
        or datetime.now(timezone.utc).isoformat(),
        "policy": policy,
        "overall_verdict": overall,
        "promise_results": promise_results,
        "audit_sha256": result.details.get("audit_sha256"),
        "manifest_sha256": result.details.get("manifest_sha256"),
        "mechanisms": mechanisms,
        "residuals": residuals,
        "anomalies": anomalies,
    }
    if next_actions:
        decision["next_actions"] = next_actions
    return decision


def add_notification(
    decision: Dict[str, Any],
    *,
    evaluation: EvaluationConfig,
    result: EvaluationResult,
) -> Dict[str, Any]:
    overall = decision.get("overall_verdict")
    action = "change_blocked" if overall in {"red", "error"} else "change_allowed"
    impact = _impact_from_severity(evaluation.severity)
    likelihood = _likelihood_from_credence(result.credence)
    confidence = _confidence_from_kroot(result.details.get("k_root"))
    summary = f"{action.replace('_', ' ')} for {evaluation.promise_id} ({overall})."
    decision["notification"] = {
        "action": action,
        "impact": impact,
        "likelihood": likelihood,
        "confidence": confidence,
        "summary": summary,
    }
    return decision


def _promise_result(
    result: EvaluationResult, evaluation: EvaluationConfig
) -> Dict[str, Any]:
    reasons = _reason_codes(result, evaluation)
    promise_result = {
        "promise_id": evaluation.promise_id,
        "threshold": evaluation.threshold,
        "credence": result.credence,
        "verdict": result.verdict,
        "k_root": result.details.get("k_root"),
        "applicable": result.details.get("applicable", True),
        "severity": evaluation.severity,
        "reason_codes": reasons,
    }
    evidence_refs = result.details.get("evidence_refs")
    if evidence_refs:
        promise_result["evidence_refs"] = evidence_refs
    if "violation_detected" in reasons:
        semgrep_refs = (evidence_refs or {}).get("semgrep", [])
        if semgrep_refs:
            promise_result["violation_evidence_refs"] = semgrep_refs
    return promise_result


def _reason_codes(result: EvaluationResult, evaluation: EvaluationConfig) -> List[str]:
    reasons: List[str] = []
    details = result.details
    gates = details.get("gates") or {}
    evidence = details.get("evidence") or {}
    if details.get("applicable") is False:
        reasons.append("not_applicable")
    if result.verdict == "error" or details.get("semgrep_error") or details.get("test_error"):
        reasons.append("tooling_error")
    if gates:
        if not gates.get("credence>=threshold", True):
            reasons.append("credence_below_threshold")
        if not gates.get("k_root>=tau", True):
            reasons.append("insufficient_support")
    if int(evidence.get("violations_found", 0) or 0) > 0:
        reasons.append("violation_detected")
    if evidence.get("tests_skipped") or float(evidence.get("semgrep_coverage", 1.0) or 0.0) < 0.5:
        if "insufficient_support" not in reasons:
            reasons.append("insufficient_support")
    return reasons


def _mechanisms(result: EvaluationResult, evaluation: EvaluationConfig) -> List[str]:
    mechanisms: List[str] = []
    gates = result.details.get("gates") or {}
    if gates.get("credence>=threshold"):
        mechanisms.append("credence_gate_pass")
    if gates.get("k_root>=tau"):
        mechanisms.append("support_gate_pass")
    reasons = _reason_codes(result, evaluation)
    for reason in reasons:
        if reason not in mechanisms:
            mechanisms.append(reason)
    return mechanisms


def _residuals(result: EvaluationResult) -> Dict[str, Any]:
    residuals: Dict[str, Any] = {}
    session = result.details.get("session") or {}
    ledger = session.get("ledger") or {}
    if "H_NOA" in ledger:
        residuals["NOA_mass"] = ledger.get("H_NOA")
    if "H_UND" in ledger:
        residuals["UND_mass"] = ledger.get("H_UND")
    return residuals


def _next_actions(promise_result: Dict[str, Any], result: EvaluationResult) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    reasons = promise_result.get("reason_codes", [])
    evidence = result.details.get("evidence") or {}
    evidence_refs = result.details.get("evidence_refs") or {}
    flattened_refs = [
        ref for refs in evidence_refs.values() for ref in (refs or [])
    ]
    missing_evidence: List[str] = []
    if evidence.get("tests_skipped"):
        missing_evidence.append("pytest")
    if float(evidence.get("semgrep_coverage", 1.0) or 0.0) < 0.5:
        missing_evidence.append("semgrep_coverage")

    anomaly_actions = result.details.get("anomaly_actions") or {}
    for key, value in anomaly_actions.items():
        action = {
            "title": f"Resolve anomaly: {key}",
            "rationale": value,
            "expected_impact": "Reduce residual uncertainty caused by anomalies.",
        }
        if flattened_refs:
            action["evidence_refs"] = flattened_refs
        else:
            action["missing_evidence"] = [f"anomaly:{key}"]
        actions.append(action)

    if "violation_detected" in reasons:
        action = {
            "title": "Fix policy violations",
            "rationale": "Static analysis detected violations of enforced rules.",
            "expected_impact": "Remove violations to satisfy hard policy gates.",
        }
        semgrep_refs = (evidence_refs or {}).get("semgrep") or []
        if semgrep_refs:
            action["evidence_refs"] = semgrep_refs
        actions.append(action)

    if "tooling_error" in reasons:
        action = {
            "title": "Resolve tooling errors",
            "rationale": "Evidence tooling returned errors during evaluation.",
            "expected_impact": "Restore evidence collection and determinism checks.",
        }
        action["missing_evidence"] = ["tooling_health"]
        actions.append(action)

    if "insufficient_support" in reasons:
        action = {
            "title": "Collect stronger evidence",
            "rationale": "Support gate failed or evidence coverage is insufficient.",
            "expected_impact": "Increase support and reduce residual uncertainty.",
        }
        if missing_evidence:
            action["missing_evidence"] = missing_evidence
        elif flattened_refs:
            action["evidence_refs"] = flattened_refs
        actions.append(action)

    if "credence_below_threshold" in reasons:
        action = {
            "title": "Improve evidence quality",
            "rationale": "Credence is below the required threshold.",
            "expected_impact": "Raise credence above policy threshold.",
        }
        if missing_evidence:
            action["missing_evidence"] = missing_evidence
        actions.append(action)

    return actions


def _overall_verdict(results: List[Dict[str, Any]]) -> str:
    verdicts = [r.get("verdict") for r in results]
    if any(v == "error" for v in verdicts):
        return "error"
    if any(v == "red" for v in verdicts):
        return "red"
    if all(v == "n/a" for v in verdicts):
        return "n/a"
    return "green"


def _impact_from_severity(severity: str | None) -> str:
    if severity in {"low", "medium", "high", "critical"}:
        return severity
    return "medium"


def _likelihood_from_credence(credence: float | None) -> str:
    if credence is None:
        return "possible"
    if credence >= 0.9:
        return "near_certain"
    if credence >= 0.66:
        return "likely"
    if credence >= 0.33:
        return "possible"
    return "unlikely"


def _confidence_from_kroot(k_root: float | None) -> str:
    if k_root is None:
        return "medium"
    if k_root >= 0.8:
        return "high"
    if k_root >= 0.5:
        return "medium"
    return "low"
