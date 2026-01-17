# ABDUCTIO Conformance Task List

This checklist maps the ABDUCTIO Core conformance changeset to actionable tasks in praevisio.

## Scope and session metadata

- [ ] CHANGE-01: Persist scope in manifest metadata and surface in CLI output.
  - Files: `src/praevisio/application/evaluation_service.py`, `src/praevisio/presentation/cli.py`
- [ ] CHANGE-04: Add session schema fields (scope, regime taxonomy/posteriors, anomalies) to manifest metadata.
  - Files: `src/praevisio/application/evaluation_service.py`

## Regime/applicability model

- [ ] CHANGE-02: Add regime taxonomy + posteriors + applicability config surface.
  - Files: `src/praevisio/domain/evaluation_config.py`, `src/praevisio/infrastructure/config.py`, `src/praevisio/application/installation_service.py`
- [ ] CHANGE-28: Add applicability caps and log cap/renormalization events.
  - Files: `src/praevisio/application/evaluation_service.py`
- [ ] CHANGE-29: Add mismatch gate + anomaly emission (A1) pre/post-run.
  - Files: `src/praevisio/application/evaluation_service.py`, `src/praevisio/presentation/cli.py`

## Canonicalization and permutation invariance

- [ ] CHANGE-03: Ensure canonical root IDs (hash of normalized statement) and deterministic ordering.
  - Files: `src/praevisio/application/evaluation_service.py`
- [ ] CHANGE-07: Store roots in canonical-ID map and ensure ordered iteration.
  - Files: `src/praevisio/application/evaluation_service.py`

## Evaluator contract (grounding + validity)

- [ ] CHANGE-06: Extend evaluator outputs to include claim_type, evidence_ids, quote_spans, k_rubric, evidence_quality, defeaters, uncertainty_source, assumptions, status.
  - Files: `src/praevisio/infrastructure/abductio_ports.py`
- [ ] CHANGE-19: Enforce no-evidence conservative movement (A=0, clamp |Δp|<=0.05) in evaluator output.
  - Files: `src/praevisio/infrastructure/abductio_ports.py`
- [ ] CHANGE-20: Add entailment label + grounding artifacts to evaluator output.
  - Files: `src/praevisio/infrastructure/abductio_ports.py`
- [ ] CHANGE-21: Provide validity inputs and ensure v applied once (if core expects it from caller).
  - Files: `src/praevisio/infrastructure/abductio_ports.py`
- [ ] CHANGE-22/24: Add rubric guardrails + UNSCOPED caps to evaluator/decomposer outputs.
  - Files: `src/praevisio/infrastructure/abductio_ports.py`
- [ ] CHANGE-37: Emit anomaly flags A1–A4 with evidence IDs + operator action.
  - Files: `src/praevisio/application/evaluation_service.py`, `src/praevisio/presentation/cli.py`
- [ ] CHANGE-38: Enforce evaluator contract completeness; log grounding failures.
  - Files: `src/praevisio/infrastructure/abductio_ports.py`

## Decomposer contract (template + coupling)

- [ ] CHANGE-12: Enforce 4 required NEC slots for every root.
  - Files: `src/praevisio/domain/evaluation_config.py`, `src/praevisio/application/evaluation_service.py`
- [ ] CHANGE-13: Mark GENERIC_FEASIBILITY nodes as low leverage.
  - Files: `src/praevisio/infrastructure/abductio_ports.py`
- [ ] CHANGE-25: Mark UNSCOPED at root/slot when template cannot be instantiated.
  - Files: `src/praevisio/infrastructure/abductio_ports.py`
- [ ] CHANGE-39: Extend decomposer outputs with role, decomp_type, coupling bucket, falsifiable flag, test procedure, overlap metadata.
  - Files: `src/praevisio/infrastructure/abductio_ports.py`

## Open-world handling

- [ ] CHANGE-26/27: Add typed residuals (NOA/UND) + mode selection and logging.
  - Files: `src/praevisio/domain/evaluation_config.py`, `src/praevisio/infrastructure/config.py`, `src/praevisio/application/installation_service.py`, `src/praevisio/application/evaluation_service.py`

## Search pipeline (deterministic)

- [ ] CHANGE-30: Introduce SEARCH as a first-class operation in adapters.
  - Files: new module(s) under `src/praevisio/infrastructure/`
- [ ] CHANGE-31: Deterministic, symmetric breadth-first query schedule.
  - Files: new module(s) + `src/praevisio/application/evaluation_service.py`
- [ ] CHANGE-32: Evidence admission + snapshot hashes for SEARCH/EVALUATE.
  - Files: `src/praevisio/infrastructure/evidence_store.py`, new search adapter(s)
- [ ] CHANGE-33: Coverage thresholds + deterministic stopping rules.
  - Files: `src/praevisio/domain/evaluation_config.py`, new search adapter(s)
- [ ] CHANGE-40: Search contract outputs (query, sources, ordering, hashes).
  - Files: new module(s) + `src/praevisio/infrastructure/evidence_store.py`

## Logging and audit

- [ ] CHANGE-42: Log arithmetic details, evidence_packet_hash, and validity artifacts in audit/manifest.
  - Files: `src/praevisio/application/evaluation_service.py`, `src/praevisio/infrastructure/evidence_store.py`

## Conformance tests

- [ ] CHANGE-43: Permutation invariance test.
  - Files: `tests/`
- [ ] CHANGE-44: No-free-probability test (DECOMPOSE/SEARCH don’t change ledger).
  - Files: `tests/`
- [ ] CHANGE-45: Anti-inflation OR fragmentation test.
  - Files: `tests/`
- [ ] CHANGE-46: Mismatch negative control test.
  - Files: `tests/`

## Docs

- [ ] Update ABDUCTIO config snippets to include new fields.
  - Files: `docs/tutorials/01-logging-basics.md`, `README.md`
