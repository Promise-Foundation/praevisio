@security @audit @tamper_evident
Feature: Tamper-evident audit log chain and report signing
  As a governance engineer
  I want audit logs to be tamper-evident and reports verifiable
  So that any modification is detectable and attributable

  Background:
    Given an evaluation run completed with an audit log
    And audit log chaining is enabled
    And report signing is enabled

  Scenario: Audit log entries are hash-chained
    When I inspect the audit log entries
    Then each entry should include "entry_hash"
    And each entry should include "prev_hash"
    And the first entry should include "prev_hash" set to "GENESIS"

  Scenario: Reordering audit entries invalidates replay
    Given an audit file from the evaluation
    When I reorder two audit log entries
    And I try to replay the audit
    Then the replay should fail with validation error
    And the error should mention "hash chain"

  Scenario: Removing an audit entry invalidates replay
    Given an audit file from the evaluation
    When I remove one audit log entry
    And I try to replay the audit
    Then the replay should fail with validation error
    And the error should mention "missing entry"

  Scenario: Signed report verifies successfully
    Given a signed evaluation report
    When I verify the report signature
    Then verification should succeed

  Scenario: Modifying the signed report fails verification
    Given a signed evaluation report
    When I modify the report content
    And I verify the report signature
    Then verification should fail
    And the error should mention "signature"
