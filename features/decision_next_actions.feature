@voi @governance @decision
Feature: Decision includes recommended remediation actions tied to weakest evidence
  As a developer
  I want the decision to tell me what to do next
  So that "blocked" is immediately actionable

  Scenario: Decision includes next_actions when any promise is red
    Given the overall verdict is "block"
    When the decision is produced
    Then it should include "next_actions"
    And each action should include "title", "rationale", and "expected_impact"
    And each action should reference evidence IDs or missing evidence types
