Feature: Evidence collection and storage
  Scenario: Collect pytest evidence
    Given a repo with passing tests
    When I run evaluation
    Then pytest evidence should be stored
    And the evidence should include exit code

  Scenario: Collect semgrep evidence
    Given a repo with semgrep rules
    When I run evaluation
    Then semgrep evidence should be stored
    And the evidence should include coverage metrics

  Scenario: Generate evidence manifest
    Given a completed evaluation run
    When I inspect the manifest
    Then it should list all evidence artifacts
    And each artifact should have a SHA-256 hash
