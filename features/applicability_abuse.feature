@governance @applicability
Feature: Applicability is derived from evidence, not self-declared
  As a governance engineer
  I want promises to be evaluated based on evidence
  So that components cannot evade enforcement by claiming not-applicable

  Scenario: Self-declared not-applicable is ignored when evidence applies
    Given a promise declares applicable as false
    And evaluation inputs indicate applicability
    When I run the applicability check
    Then the report should include an anomaly "applicability_override_ignored"
    And the evaluation should remain applicable
