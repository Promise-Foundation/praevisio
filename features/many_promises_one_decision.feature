@governance @ci_gate @multi_promise
Feature: CI gate evaluates multiple promises and produces a single overall decision
  As a governance engineer
  I want CI to evaluate all configured promises
  So that merges are blocked based on policy, not a single promise

  Background:
    Given a configuration listing promises "llm-input-logging" and "llm-privacy-redaction" and "llm-prompt-injection-defense"
    And severity thresholds are configured for "high"

  Scenario: CI gate emits per-promise results plus an overall verdict
    When I run "praevisio ci-gate . --fail-on-violation --config .praevisio.yaml --output logs/ci-gate-report.json"
    Then "logs/ci-gate-report.json" should contain a list of results for all configured promises
    And it should include an "overall_verdict"
    And it should include "policy_id" or a hash of the policy rules used

  Scenario: Overall verdict blocks when any critical high-severity promise fails
    Given "llm-input-logging" is critical and severity "high"
    And "llm-input-logging" verdict is "red"
    When I run the CI gate with fail-on-violation enabled
    Then the CI gate should exit non-zero
    And the overall verdict should be "block"

  Scenario: Overall verdict allows when all critical promises pass
    Given all critical promises have verdict "green"
    When I run the CI gate with fail-on-violation enabled
    Then the CI gate should pass
    And the overall verdict should be "allow"
