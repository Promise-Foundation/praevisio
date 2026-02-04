Feature: CI governance gate for high-severity promises
  As a governance engineer
  I want Praevisio to act as a CI gate
  So that high-severity promises block merges when they are violated

  Background:
    Given a high-severity logging promise "llm-input-logging" with threshold 0.95

  @ci_gate @happy_path
  Scenario: CI gate passes when high-severity promise credence meets threshold
    And the evaluation credence will be 0.97
    When I run the CI gate for severity "high" with enforcement enabled
    Then the CI gate should pass
    And the report should contain a "green" verdict for promise "llm-input-logging"

  @ci_gate @violation
  Scenario: CI gate fails when high-severity promise credence is below threshold
    And the evaluation credence will be 0.70
    When I run the CI gate for severity "high" with enforcement enabled
    Then the CI gate should fail
    And the report should contain a "red" verdict for promise "llm-input-logging"
