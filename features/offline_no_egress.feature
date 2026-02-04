@security @privacy @offline
Feature: Offline mode prevents network egress
  As a diligence user
  I want Praevisio to run without network access
  So that sensitive information cannot leave my environment

  Background:
    Given a repository with runnable local evidence tools
    And offline mode is enabled

  Scenario: Offline run succeeds using only local tools
    When I run "praevisio evaluate-commit . --config .praevisio.yaml --offline"
    Then the evaluation should complete successfully
    And the manifest should record "egress_policy" as "offline"

  Scenario: Any attempted network call fails the run
    Given a component that attempts an outbound network request
    When I run "praevisio evaluate-commit . --config .praevisio.yaml --offline"
    Then the evaluation should fail
    And the error should mention "egress violation"

  Scenario: Offline mode produces an auditable enforcement record
    When I run "praevisio evaluate-commit . --config .praevisio.yaml --offline --json"
    Then the audit file should include an "egress_enforcement" record
    And the record should include the enforcement outcome "blocked_or_none_attempted"
