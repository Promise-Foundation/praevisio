@abductio @governance @residuals
Feature: Decision explains PASS vs FAIL mechanisms and residual mass explicitly
  As a diligence user
  I want to understand whether failure is due to violations, weak evidence, or residual uncertainty
  So that remediation is correct

  Scenario: PASS when all required slots pass and residual mass is acceptable
    Given all required slots have p above their minima
    And the root credence is above threshold
    And residual mass assigned to NOA is below the policy limit
    When I run evaluation
    Then the verdict should be "green"
    And the decision should include "mechanisms" listing which gates were satisfied
    And the decision should record "residuals" including "NOA_mass"

  Scenario: FAIL due to explicit policy violation (hard fail mechanism)
    Given semgrep finds at least 1 violation of "llm-call-must-log"
    When I run evaluation
    Then the verdict should be "red"
    And the decision should include a mechanism "violation_detected"
    And it should list evidence references for the violating finding

  Scenario: FAIL due to weak support (soft fail mechanism)
    Given there are no explicit violations
    But tests are skipped and coverage is low
    When I run evaluation
    Then the verdict should be "red"
    And the decision should include a mechanism "insufficient_support"
    And it should include recommended next actions

  Scenario: FAIL due to excessive residual uncertainty
    Given applicability fit is low across all roots
    And residual mass exceeds the policy limit
    When I run evaluation
    Then the decision should include anomaly "library_mismatch" or "underdetermined"
    And the verdict should be "red" or "yellow" according to policy
