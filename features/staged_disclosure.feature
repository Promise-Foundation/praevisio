@diligence @evidence @staged_disclosure
Feature: Staged evidence disclosure prevents anchoring and conclusion leakage
  As a diligence lead
  I want evaluators to see evidence in controlled stages
  So that conclusions do not leak into scoring

  Background:
    Given an evidence bundle with "observations", "appendices", and "conclusions"
    And staged disclosure is enabled

  Scenario: Phase A scoring uses observations only
    When I run evaluation in Phase A
    Then the evaluator input should include only "observations"
    And the audit should record "evidence_stage" as "observations_only"

  Scenario: Conclusions are blocked before Phase A lock
    Given Phase A is not locked
    When a component requests "conclusions"
    Then the request should be denied
    And the audit should include an "evidence_access_violation" anomaly

  Scenario: Phase B allows oracle comparison after lock
    Given Phase A is locked
    When I run Phase B oracle comparison
    Then conclusions may be used
    And the audit should record "evidence_stage" as "oracle_comparison"
