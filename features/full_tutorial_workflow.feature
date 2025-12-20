Feature: Complete tutorial workflow
  Scenario: Tutorial 1 - Hello World
    Given a fresh tutorial repository
    And I create the boundary module
    And I create the test file
    And I create the semgrep rules
    And I create the promise file
    And I create the config file
    When I run "praevisio evaluate-commit . --config .praevisio.yaml --json"
    Then the evaluation should pass
    And the verdict should be "green"
    And the audit file should exist
    And I can replay the audit

  Scenario: Tutorial 1 - Simulate violation
    Given a tutorial repository with logging boundary
    When I remove the log call from the boundary
    And I run "praevisio evaluate-commit . --config .praevisio.yaml --json"
    Then the evaluation should fail
    And the verdict should be "red"
    And semgrep should report 1 violation
