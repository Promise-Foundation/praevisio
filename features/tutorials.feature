Feature: Tutorial workflows
  Ensure the tutorials reflect real, runnable workflows.

  Scenario: Tutorial evaluation passes with pytest evidence
    Given a tutorial repo with passing tests
    And the evaluation service uses a fake analyzer
    When I run the tutorial evaluation
    Then the verdict should be "green"
    And audit and manifest artifacts should exist
    And replaying the audit should include the promise id

  Scenario: Tutorial evaluation fails when tests fail
    Given a tutorial repo with failing tests
    And the evaluation service uses a fake analyzer
    When I run the tutorial evaluation
    Then the verdict should be "red"
