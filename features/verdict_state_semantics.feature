@governance @verdict
Feature: Verdict state machine is explicit and consistent
  As a governance engineer
  I want verdict semantics to be stable across CLI, CI, and exported artifacts
  So that "green/red/error/na" always means the same thing

  Scenario: Green when all gates pass for an applicable promise
    Given an applicable promise evaluation
    And credence is above the threshold
    And k_root is above tau
    When I run evaluation
    Then the promise verdict should be "green"
    And the overall verdict should be "allow"

  Scenario: Red when credence gate fails
    Given an applicable promise evaluation
    And credence is below the threshold
    When I run evaluation
    Then the promise verdict should be "red"
    And the decision should include a reason code "credence_below_threshold"

  Scenario: Red when k_root gate fails
    Given an applicable promise evaluation
    And credence is above the threshold
    And k_root is below tau
    When I run evaluation
    Then the promise verdict should be "red"
    And the decision should include a reason code "insufficient_support"

  Scenario: Error when evidence tooling errors
    Given semgrep fails to run or returns an error
    When I run evaluation
    Then the promise verdict should be "error"
    And the decision should include a reason code "tooling_error"
    And the CI gate should fail when fail-on-violation is enabled

  Scenario: Not applicable does not block
    Given the promise is not applicable to this repository
    When I run evaluation
    Then the promise verdict should be "n/a"
    And the overall decision should not be blocked by this promise
