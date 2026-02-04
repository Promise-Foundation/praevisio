@audit @determinism @replay
Feature: Toolchain determinism is recorded and enforced
  As a governance engineer
  I want toolchain versions and environment details recorded
  So that results are reproducible and drift is detectable

  Background:
    Given a completed evaluation run

  Scenario: Manifest records toolchain versions and environment
    When I inspect the manifest
    Then the manifest should include "tool_versions"
    And the manifest should include "os"
    And the manifest should include "python_version"
    And the manifest should include "praevisio_version"

  Scenario: Replay fails or warns when toolchain differs
    Given an audit file from the evaluation
    And my current toolchain versions differ from the recorded manifest
    When I replay the audit
    Then the replay should produce a determinism warning or fail
    And the output should mention "toolchain mismatch"

  Scenario: Strict replay fails on toolchain mismatch
    Given an audit file from the evaluation
    And my current toolchain versions differ from the recorded manifest
    And strict determinism is enabled for replay
    When I replay the audit
    Then the replay should fail due to determinism mismatch
    And the output should mention "toolchain mismatch"

  Scenario: Determinism anomaly is emitted on nondeterministic evidence
    Given an evidence collector that produces nondeterministic output
    When I run evaluation with nondeterministic evidence
    Then the report should include an anomaly "toolchain_nondeterminism"
    And the anomaly should include an operator action

  Scenario: Strict determinism fails closed on mismatch
    Given an evidence collector that uses randomness unless seeded
    And determinism mode is "strict"
    When I run evaluation with nondeterministic evidence
    Then the evaluation should fail closed
    And the report should include an anomaly "toolchain_nondeterminism"
    And the anomaly should include an operator action

  Scenario: Determinism seed stabilizes nondeterministic evidence
    Given an evidence collector that uses randomness unless seeded
    And determinism seed is set to 123
    And determinism mode is "strict"
    When I run evaluation with nondeterministic evidence
    Then the determinism checks should pass
