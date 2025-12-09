Feature: Local pre-commit governance gate
  As a developer
  I want Praevisio to run as a pre-commit hook
  So that critical promises block bad commits on my machine

  Background:
    Given a git working directory with no existing pre-commit hook
    And a critical logging promise "llm-input-logging" with threshold 0.95

  @precommit @install
  Scenario: Installing the Praevisio pre-commit hook
    When I run "praevisio install-hooks"
    Then a git pre-commit hook should be installed
    And the pre-commit hook should invoke "praevisio pre-commit"

  @precommit @happy_path
  Scenario: Pre-commit gate passes when critical promises are satisfied
    And the evaluation credence for critical promises will be 0.97
    When I run "praevisio pre-commit"
    Then the pre-commit gate should pass

  @precommit @violation
  Scenario: Pre-commit gate fails when a critical promise is violated
    And the evaluation credence for critical promises will be 0.70
    When I run "praevisio pre-commit"
    Then the pre-commit gate should fail
