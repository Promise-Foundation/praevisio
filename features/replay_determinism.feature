Feature: Deterministic audit replay
  Scenario: Replay produces same credence
    Given an evaluation with credence 0.95
    And an audit file from that evaluation
    When I replay the audit
    Then the replayed credence should equal 0.95

  Scenario: Replay with modified audit fails
    Given an evaluation audit file
    When I corrupt the audit file
    And I try to replay it
    Then the replay should fail with validation error
