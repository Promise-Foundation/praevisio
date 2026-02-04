@governance @decision @verdict
Feature: Governance decision artifact records verdicts, policy, and rationale
  As a diligence user
  I want every run to produce a canonical decision.json
  So that "change blocked" is explainable, replayable, and verifiable

  Background:
    Given a Praevisio configuration with severity thresholds
    And the run artifacts directory is ".praevisio/runs"

  Scenario: A run produces decision.json with overall verdict and per-promise outcomes
    When I run "praevisio evaluate-commit . --config .praevisio.yaml --json"
    Then the latest run directory should contain "manifest.json"
    And it should contain "audit.json"
    And it should contain "decision.json"
    And "decision.json" should include "schema_version"
    And it should include "run_id"
    And it should include "timestamp_utc"
    And it should include "policy" describing thresholds and enforcement rules
    And it should include an "overall_verdict"
    And it should include a list "promise_results"
    And each promise result should include "promise_id", "threshold", "credence", and "verdict"
    And "decision.json" should reference "audit_sha256" and "manifest_sha256"

  Scenario: Decision includes video-grade notification fields
    Given the evaluation is for a promise with severity "high"
    When I run "praevisio ci-gate . --fail-on-violation --config .praevisio.yaml"
    Then "decision.json" should include "notification"
    And "notification" should include "action" as "change_blocked" or "change_allowed"
    And "notification" should include "impact" as one of "low|medium|high|critical"
    And "notification" should include "likelihood" as one of "unlikely|possible|likely|near_certain"
    And "notification" should include "confidence" as one of "low|medium|high"
    And the notification payload should include a human-readable "summary"

  Scenario: Decision is deterministic under replay
    Given I have the latest run's "audit.json"
    When I run "praevisio replay-audit --latest --json"
    Then the replayed ledger should reproduce the same credence values used in "decision.json"
    And the recomputed "overall_verdict" should match "decision.json"
