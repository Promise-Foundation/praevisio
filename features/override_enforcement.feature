@override @gate
Feature: Override enforcement for high-severity gates
  As a governance engineer
  I want overrides to expire and require compensating controls
  So that high-impact exceptions remain accountable and bounded

  Scenario: Expired override does not unblock a high-severity gate
    Given a high-severity red evaluation result
    And an override expires at "2020-01-01T00:00:00Z"
    And the override includes compensating controls
    When I apply the override to the CI gate
    Then the gate should remain blocked

  Scenario: Missing compensating controls prevents override on high severity
    Given a high-severity red evaluation result
    And an override expires at "2026-12-31T00:00:00Z"
    And the override lacks compensating controls
    When I apply the override to the CI gate
    Then the gate should remain blocked

  Scenario: Valid override with compensating controls unblocks
    Given a high-severity red evaluation result
    And an override expires at "2026-12-31T00:00:00Z"
    And the override includes compensating controls
    When I apply the override to the CI gate
    Then the override should unblock the gate
