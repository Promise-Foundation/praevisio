from __future__ import annotations

import hashlib
import json
import os
import random
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple, Iterator

from abductio_core.application.dto import RootSpec, SessionConfig, SessionRequest
from abductio_core.application.ports import RunSessionDeps
from abductio_core.application.use_cases.run_session import run_session
import abductio_core

from ..domain.entities import EvaluationResult, StaticAnalysisResult
from ..domain.evaluation_config import EvaluationConfig
from ..domain.ports import StaticAnalyzer, TestRunner, PromiseLoader
from ..infrastructure.abductio_ports import (
    DeterministicDecomposer,
    DeterministicEvaluator,
    DeterministicSearcher,
    ListAuditSink,
)
from ..infrastructure.evidence_store import EvidenceStore
from ..infrastructure.promise_loader import YamlPromiseLoader
from ..infrastructure.report_signing import sign_bytes
from ..infrastructure.static_analysis_semgrep import SemgrepStaticAnalyzer
from ..infrastructure.test_runner_subprocess import SubprocessPytestRunner
from ..infrastructure.toolchain import current_toolchain_metadata
from ..infrastructure.audit_chain import chain_audit_log
from ..infrastructure.offline_guard import offline_guard, EgressViolation, OfflineEnforcement


@dataclass(frozen=True)
class EvidenceCollection:
    evidence: Dict[str, Any]
    pytest_payload: Dict[str, Any]
    semgrep_payload: Dict[str, Any]
    static_skipped: bool
    test_error: str | None
    sa_result: StaticAnalysisResult


class EvaluationService:
    """Evaluate a commit using abductio-core for credence + audit."""

    def __init__(
        self,
        analyzer: StaticAnalyzer | None = None,
        test_runner: TestRunner | None = None,
        promise_loader: PromiseLoader | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._test_runner = test_runner or SubprocessPytestRunner()
        self._promise_loader = promise_loader

    def evaluate_path(self, path: str, config: EvaluationConfig | None = None) -> EvaluationResult:
        evaluation = config or EvaluationConfig()
        repo_root = Path(path)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        run_root = repo_root / evaluation.run_dir / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        evidence_store = EvidenceStore(run_root, hash_only=evaluation.hash_only_evidence)

        promise = None
        promise_error = None
        try:
            loader = self._promise_loader or YamlPromiseLoader(
                base_path=repo_root / "governance" / "promises"
            )
            promise = loader.load(evaluation.promise_id)
        except Exception as exc:
            promise_error = str(exc)

        manifest_metadata = {
            "run_id": run_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "praevisio_version": self._praevisio_version(),
            "abductio_core_version": getattr(abductio_core, "__version__", "unknown"),
            "session_config": {
                "credits": evaluation.abductio_credits,
                "tau": evaluation.abductio_tau,
                "epsilon": evaluation.abductio_epsilon,
                "gamma": evaluation.abductio_gamma,
                "gamma_noa": evaluation.abductio_gamma_noa,
                "gamma_und": evaluation.abductio_gamma_und,
                "alpha": evaluation.abductio_alpha,
                "beta": evaluation.abductio_beta,
                "W": evaluation.abductio_weight_cap,
                "lambda_voi": evaluation.abductio_lambda_voi,
                "world_mode": evaluation.abductio_world_mode,
                "required_slots": list(evaluation.abductio_required_slots),
            },
        }
        toolchain_metadata = current_toolchain_metadata()
        manifest_metadata.update(
            {
                "tool_versions": toolchain_metadata.get("tool_versions"),
                "os": toolchain_metadata.get("os"),
                "python_version": toolchain_metadata.get("python_version"),
            }
        )
        manifest_metadata["evidence_retention"] = (
            "hash_only" if evaluation.hash_only_evidence else "standard"
        )
        egress_policy = "offline" if evaluation.offline else "standard"
        manifest_metadata["egress_policy"] = egress_policy

        egress_state = OfflineEnforcement()
        try:
            with offline_guard(evaluation.offline) as egress_state:
                if promise_error:
                    manifest_path, manifest_sha = evidence_store.write_manifest(
                        metadata=manifest_metadata
                    )
                    details = self._details(
                        evaluation=evaluation,
                        evidence={},
                        evidence_refs={},
                        applicable=self._derive_applicability(evaluation),
                        semgrep_skipped=True,
                        audit_path=None,
                        audit_sha=None,
                        manifest_path=manifest_path,
                        manifest_sha=manifest_sha,
                        run_id=run_id,
                        session_result=None,
                        promise=promise,
                        promise_error=promise_error,
                    )
                    details = self._augment_details_for_egress(
                        details, egress_policy, None, None
                    )
                    return EvaluationResult(
                        credence=0.0,
                        verdict="error",
                        details=details,
                    )

                analyzer, semgrep_rules_path = self._build_analyzer(evaluation, self._analyzer)
                anomalies: List[str] = []
                derived_applicable = self._derive_applicability(evaluation)
                applicable = derived_applicable
                if (
                    promise is not None
                    and promise.applicable is not None
                    and promise.applicable != derived_applicable
                ):
                    anomalies.append("applicability_override_ignored")
                anomaly_actions: Dict[str, str] = {}

                collection = self._collect_evidence_payloads(
                    path, evaluation, analyzer, semgrep_rules_path
                )
                determinism = {
                    "runs": evaluation.determinism_runs,
                    "mode": evaluation.determinism_mode,
                    "seed": evaluation.determinism_seed,
                    "mismatch": False,
                }
                if evaluation.determinism_runs > 1:
                    base_digest = self._evidence_digest(collection)
                    for _ in range(1, evaluation.determinism_runs):
                        other = self._collect_evidence_payloads(
                            path, evaluation, analyzer, semgrep_rules_path
                        )
                        if self._evidence_digest(other) != base_digest:
                            determinism["mismatch"] = True
                            anomalies.append("toolchain_nondeterminism")
                            break
                if "toolchain_nondeterminism" in anomalies:
                    anomaly_actions["toolchain_nondeterminism"] = (
                        "Re-run with pinned toolchain or set determinism_seed."
                    )

                pytest_path = "evidence/pytest.json"
                semgrep_path = "evidence/semgrep.json"
                pytest_ref = evidence_store.write_json(
                    pytest_path, collection.pytest_payload, kind="pytest"
                )
                semgrep_ref = evidence_store.write_json(
                    semgrep_path, collection.semgrep_payload, kind="semgrep"
                )

                evidence = collection.evidence
                evidence_refs = {"pytest": [pytest_ref], "semgrep": [semgrep_ref]}
                pointer_map = {
                    pytest_ref: pytest_path,
                    semgrep_ref: semgrep_path,
                }
                evidence_items = self._sorted_evidence_items(
                    [
                        {
                            "id": ref,
                            "source": kind,
                            "text": "",
                            "metadata": {"pointer": pointer_map.get(ref)},
                        }
                        for kind, refs in evidence_refs.items()
                        for ref in refs
                    ]
                )

                manifest_path = None
                manifest_sha = None
                audit_path = None
                audit_sha = None

                if collection.sa_result.error or collection.test_error:
                    manifest_path, manifest_sha = evidence_store.write_manifest(
                        metadata=manifest_metadata
                    )
                    details = self._details(
                        evaluation=evaluation,
                        evidence=evidence,
                        evidence_refs=evidence_refs,
                        applicable=applicable,
                        semgrep_skipped=collection.static_skipped,
                        audit_path=audit_path,
                        audit_sha=audit_sha,
                        manifest_path=manifest_path,
                        manifest_sha=manifest_sha,
                        run_id=run_id,
                        session_result=None,
                        promise=promise,
                        promise_error=promise_error,
                        determinism=determinism,
                        anomalies=anomalies,
                        anomaly_actions=anomaly_actions,
                    )
                    details = self._augment_details_for_egress(
                        details, egress_policy, None, None
                    )
                    return EvaluationResult(
                        credence=0.0,
                        verdict="error",
                        details=details,
                    )
                if determinism["mismatch"] and evaluation.determinism_mode == "strict":
                    manifest_path, manifest_sha = evidence_store.write_manifest(
                        metadata=manifest_metadata
                    )
                    details = self._details(
                        evaluation=evaluation,
                        evidence=evidence,
                        evidence_refs=evidence_refs,
                        applicable=applicable,
                        semgrep_skipped=collection.static_skipped,
                        audit_path=audit_path,
                        audit_sha=audit_sha,
                        manifest_path=manifest_path,
                        manifest_sha=manifest_sha,
                        run_id=run_id,
                        session_result=None,
                        promise=promise,
                        promise_error=promise_error,
                        determinism=determinism,
                        anomalies=anomalies,
                        anomaly_actions=anomaly_actions,
                    )
                    details = self._augment_details_for_egress(
                        details, egress_policy, None, None
                    )
                    return EvaluationResult(
                        credence=0.0,
                        verdict="error",
                        details=details,
                    )

                audit_sink = ListAuditSink()
                evaluator = DeterministicEvaluator(
                    evidence=evidence, evidence_refs=evidence_refs
                )
                decomposer = DeterministicDecomposer(
                    promise_statement=f"Promise {evaluation.promise_id} holds for {repo_root}",
                    slot_statements={},
                )
                session = SessionRequest(
                    scope=f"Commit at {repo_root} satisfies promise {evaluation.promise_id}",
                    roots=[
                        RootSpec(
                            root_id=evaluation.promise_id,
                            statement=f"Promise {evaluation.promise_id} is satisfied",
                            exclusion_clause="Not explained by other hypotheses",
                        )
                    ],
                    config=SessionConfig(
                        tau=evaluation.abductio_tau,
                        epsilon=evaluation.abductio_epsilon,
                        gamma_noa=evaluation.abductio_gamma_noa,
                        gamma_und=evaluation.abductio_gamma_und,
                        gamma=evaluation.abductio_gamma,
                        alpha=evaluation.abductio_alpha,
                        beta=evaluation.abductio_beta,
                        W=evaluation.abductio_weight_cap,
                        lambda_voi=evaluation.abductio_lambda_voi,
                        world_mode=evaluation.abductio_world_mode,
                    ),
                    credits=evaluation.abductio_credits,
                    required_slots=self._sorted_required_slots(
                        evaluation.abductio_required_slots
                    ),
                    run_mode="until_credits_exhausted",
                    evidence_items=evidence_items,
                )
                searcher = DeterministicSearcher()
                result = run_session(
                    session,
                    RunSessionDeps(
                        evaluator=evaluator,
                        decomposer=decomposer,
                        audit_sink=audit_sink,
                        searcher=searcher,
                    ),
                )
                credence = float(result.ledger.get(evaluation.promise_id, 0.0))
                root_view = result.roots.get(evaluation.promise_id, {})
                k_root = float(root_view.get("k_root", 0.0))
                gates = {
                    "credence>=threshold": credence >= evaluation.threshold,
                    "k_root>=tau": k_root >= evaluation.abductio_tau,
                }
                verdict = "green" if all(gates.values()) else "red"

                audit_payload = result.audit
                egress_outcome = (
                    "blocked_or_none_attempted" if evaluation.offline else None
                )
                if evaluation.offline:
                    audit_payload = self._append_audit_event(
                        audit_payload,
                        self._egress_event(
                            policy=egress_policy,
                            outcome=egress_outcome,
                            attempted=egress_state.attempted,
                            error=egress_state.last_error,
                        ),
                    )
                audit_payload = chain_audit_log(audit_payload)
                audit_path = run_root / "audit.json"
                audit_text = json.dumps(audit_payload, indent=2, sort_keys=True)
                audit_bytes = audit_text.encode("utf-8")
                audit_path.write_bytes(audit_bytes)
                audit_sha = hashlib.sha256(audit_bytes).hexdigest()
                evidence_store.record_external("audit", audit_path, audit_sha)

                report_payload = {
                    "run_id": run_id,
                    "promise_id": evaluation.promise_id,
                    "credence": credence,
                    "verdict": verdict,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                }
                report_text = json.dumps(report_payload, indent=2, sort_keys=True)
                report_ref = evidence_store.write_text(
                    "report.json", report_text, kind="report"
                )
                report_sig = sign_bytes(report_text.encode("utf-8"))
                report_sig_ref = evidence_store.write_text(
                    "report.sig", report_sig, kind="report_signature"
                )
                report_path = run_root / "report.json"
                report_sig_path = run_root / "report.sig"

                manifest_path, manifest_sha = evidence_store.write_manifest(
                    metadata=manifest_metadata
                )

                details = self._details(
                    evaluation=evaluation,
                    evidence=evidence,
                    evidence_refs=evidence_refs,
                    applicable=applicable,
                    semgrep_skipped=collection.static_skipped,
                    audit_path=audit_path,
                    audit_sha=audit_sha,
                    manifest_path=manifest_path,
                    manifest_sha=manifest_sha,
                    run_id=run_id,
                    session_result=result.to_dict_view(),
                    gates=gates,
                    k_root=k_root,
                    promise=promise,
                    promise_error=promise_error,
                    determinism=determinism,
                    anomalies=anomalies,
                    anomaly_actions=anomaly_actions,
                    report_path=report_path,
                    report_signature_path=report_sig_path,
                )
                details = self._augment_details_for_egress(
                    details, egress_policy, egress_outcome, None
                )
                return EvaluationResult(
                    credence=credence,
                    verdict=verdict,
                    details=details,
                )
        except EgressViolation as exc:
            error_message = str(exc)
            egress_outcome = "blocked_or_none_attempted"
            audit_payload = self._append_audit_event(
                [],
                self._egress_event(
                    policy=egress_policy,
                    outcome=egress_outcome,
                    attempted=egress_state.attempted,
                    error=error_message,
                ),
            )
            audit_payload = chain_audit_log(audit_payload)
            audit_path = run_root / "audit.json"
            audit_text = json.dumps(audit_payload, indent=2, sort_keys=True)
            audit_bytes = audit_text.encode("utf-8")
            audit_path.write_bytes(audit_bytes)
            audit_sha = hashlib.sha256(audit_bytes).hexdigest()
            evidence_store.record_external("audit", audit_path, audit_sha)
            manifest_path, manifest_sha = evidence_store.write_manifest(
                metadata=manifest_metadata
            )
            details = self._details(
                evaluation=evaluation,
                evidence={},
                evidence_refs={},
                applicable=self._derive_applicability(evaluation),
                semgrep_skipped=True,
                audit_path=audit_path,
                audit_sha=audit_sha,
                manifest_path=manifest_path,
                manifest_sha=manifest_sha,
                run_id=run_id,
                session_result=None,
                promise=promise,
                promise_error=promise_error,
            )
            details = self._augment_details_for_egress(
                details, egress_policy, egress_outcome, error_message
            )
            return EvaluationResult(
                credence=0.0,
                verdict="error",
                details=details,
            )

    @staticmethod
    def _build_analyzer(
        evaluation: EvaluationConfig,
        analyzer_override: StaticAnalyzer | None,
    ) -> Tuple[StaticAnalyzer | None, str]:
        semgrep_rules_path = evaluation.semgrep_rules_path
        if analyzer_override is not None:
            return analyzer_override, semgrep_rules_path
        if not semgrep_rules_path:
            return None, ""
        if not evaluation.semgrep_callsite_rule_id or not evaluation.semgrep_violation_rule_id:
            return None, semgrep_rules_path
        analyzer = SemgrepStaticAnalyzer(
            rules_path=Path(semgrep_rules_path),
            callsite_rule_id=evaluation.semgrep_callsite_rule_id,
            violation_rule_id=evaluation.semgrep_violation_rule_id,
        )
        return analyzer, semgrep_rules_path

    @staticmethod
    def _sorted_required_slots(slots: List[Dict[str, str]]) -> List[Dict[str, str]]:
        return sorted(
            [dict(slot) for slot in slots],
            key=lambda slot: (slot.get("slot_key", ""), slot.get("role", "")),
        )

    @staticmethod
    def _sorted_evidence_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            [dict(item) for item in items],
            key=lambda item: (item.get("id", ""), item.get("source", "")),
        )

    @staticmethod
    def _derive_applicability(evaluation: EvaluationConfig) -> bool:
        has_tests = bool(evaluation.pytest_targets)
        has_rules = bool(evaluation.semgrep_rules_path) and bool(
            evaluation.semgrep_callsite_rule_id and evaluation.semgrep_violation_rule_id
        )
        return has_tests or has_rules

    @contextmanager
    def _determinism_seed(self, seed: int | None) -> Iterator[None]:
        if seed is None:
            yield
            return
        prior_seed = os.environ.get("PRAEVISIO_SEED")
        prior_state = random.getstate()
        os.environ["PRAEVISIO_SEED"] = str(seed)
        random.seed(seed)
        try:
            yield
        finally:
            if prior_seed is None:
                os.environ.pop("PRAEVISIO_SEED", None)
            else:
                os.environ["PRAEVISIO_SEED"] = prior_seed
            random.setstate(prior_state)

    def _collect_evidence_payloads(
        self,
        path: str,
        evaluation: EvaluationConfig,
        analyzer: StaticAnalyzer | None,
        semgrep_rules_path: str,
    ) -> EvidenceCollection:
        with self._determinism_seed(evaluation.determinism_seed):
            test_passes, tests_skipped, test_exit_code, test_error = self._run_tests(
                path, evaluation
            )

            static_skipped = False
            if analyzer is None:
                if not semgrep_rules_path:
                    static_skipped = True
                    sa_result = StaticAnalysisResult(
                        total_llm_calls=0, violations=0, coverage=0.0, findings=[]
                    )
                else:
                    sa_result = StaticAnalysisResult(
                        total_llm_calls=0,
                        violations=0,
                        coverage=0.0,
                        findings=[],
                        error="semgrep rule ids not configured",
                    )
            else:
                sa_result = analyzer.analyze(path)

        pytest_payload = {
            "targets": list(evaluation.pytest_targets),
            "args": list(evaluation.pytest_args),
            "exit_code": test_exit_code,
            "skipped": tests_skipped,
            "error": test_error,
        }

        semgrep_payload = {
            "rules_path": semgrep_rules_path,
            "callsite_rule_id": evaluation.semgrep_callsite_rule_id,
            "violation_rule_id": evaluation.semgrep_violation_rule_id,
            "coverage": sa_result.coverage,
            "total_calls": sa_result.total_llm_calls,
            "violations": sa_result.violations,
            "error": sa_result.error,
            "skipped": static_skipped,
            "findings": [f.__dict__ for f in sa_result.findings],
        }

        evidence = {
            "test_passes": test_passes,
            "tests_skipped": tests_skipped,
            "tests_configured": bool(evaluation.pytest_targets),
            "test_error": test_error,
            "semgrep_coverage": sa_result.coverage,
            "violations_found": sa_result.violations,
            "total_llm_calls": sa_result.total_llm_calls,
            "semgrep_error": sa_result.error,
            "semgrep_rules_configured": bool(semgrep_rules_path),
            "no_call_sites": sa_result.total_llm_calls == 0 and sa_result.error is None,
        }
        return EvidenceCollection(
            evidence=evidence,
            pytest_payload=pytest_payload,
            semgrep_payload=semgrep_payload,
            static_skipped=static_skipped,
            test_error=test_error,
            sa_result=sa_result,
        )

    @staticmethod
    def _evidence_digest(collection: EvidenceCollection) -> str:
        payload = {
            "pytest": collection.pytest_payload,
            "semgrep": collection.semgrep_payload,
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _run_tests(
        self, path: str, evaluation: EvaluationConfig
    ) -> tuple[bool | None, bool, int | None, str | None]:
        if not evaluation.pytest_targets:
            return None, True, None, None
        try:
            test_result_code = self._test_runner.run(
                path, [*evaluation.pytest_targets, *evaluation.pytest_args]
            )
            return test_result_code == 0, False, test_result_code, None
        except Exception as exc:  # pragma: no cover - defensive
            return False, False, None, str(exc)

    @staticmethod
    def _details(
        evaluation: EvaluationConfig,
        evidence: Dict[str, Any],
        evidence_refs: Dict[str, List[str]],
        applicable: bool,
        semgrep_skipped: bool,
        audit_path: Path | None,
        audit_sha: str | None,
        manifest_path: Path | None,
        manifest_sha: str | None,
        run_id: str,
        session_result: Dict[str, Any] | None,
        gates: Dict[str, bool] | None = None,
        k_root: float | None = None,
        promise: "Promise | None" = None,
        promise_error: str | None = None,
        determinism: Dict[str, Any] | None = None,
        anomalies: List[str] | None = None,
        anomaly_actions: Dict[str, str] | None = None,
        report_path: Path | None = None,
        report_signature_path: Path | None = None,
    ) -> Dict[str, Any]:
        promise_payload = None
        if promise is not None:
            promise_payload = {
                "id": promise.id,
                "statement": promise.statement,
                "version": promise.version,
                "domain": promise.domain,
                "critical": promise.critical,
                "credence_threshold": promise.credence_threshold,
            }
        return {
            "promise_id": evaluation.promise_id,
            "threshold": evaluation.threshold,
            "severity": evaluation.severity,
            "applicable": applicable,
            "semgrep_skipped": semgrep_skipped,
            "semgrep_error": evidence.get("semgrep_error"),
            "test_error": evidence.get("test_error"),
            "evidence": dict(evidence),
            "evidence_refs": dict(evidence_refs),
            "promise": promise_payload,
            "promise_error": promise_error,
            "audit_path": str(audit_path) if audit_path else None,
            "audit_sha256": audit_sha,
            "manifest_path": str(manifest_path) if manifest_path else None,
            "manifest_sha256": manifest_sha,
            "run_id": run_id,
            "session": session_result,
            "gates": gates,
            "k_root": k_root,
            "determinism": dict(determinism) if determinism else None,
            "anomalies": list(anomalies) if anomalies else [],
            "anomaly_actions": dict(anomaly_actions) if anomaly_actions else {},
            "report_path": str(report_path) if report_path else None,
            "report_signature_path": str(report_signature_path) if report_signature_path else None,
        }

    @staticmethod
    def _augment_details_for_egress(
        details: Dict[str, Any],
        policy: str | None,
        outcome: str | None,
        error: str | None,
    ) -> Dict[str, Any]:
        if policy:
            details["egress_policy"] = policy
        if outcome:
            details["egress_outcome"] = outcome
        if error:
            details["egress_error"] = error
        return details

    @staticmethod
    def _egress_event(
        *,
        policy: str,
        outcome: str | None,
        attempted: bool,
        error: str | None = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "policy": policy,
            "outcome": outcome,
            "attempted": attempted,
        }
        if error:
            payload["error"] = error
        return {"event_type": "egress_enforcement", "payload": payload}

    @staticmethod
    def _append_audit_event(audit: Any, event: Dict[str, Any]) -> Any:
        if isinstance(audit, dict) and isinstance(audit.get("events"), list):
            events = list(audit["events"])
            events.append(event)
            return {"events": events}
        if isinstance(audit, list):
            return [*audit, event]
        return [event]

    @staticmethod
    def _praevisio_version() -> str:
        try:
            from .. import __version__ as version
            return version
        except Exception:
            return "unknown"
