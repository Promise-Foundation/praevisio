@security @privacy @evidence
Feature: Hash-only evidence retention for sensitive environments
  As a governance engineer
  I want Praevisio to retain evidence as hashes and pointers
  So that audits remain possible without storing sensitive raw data

  Background:
    Given a completed evaluation run
    And hash-only evidence retention is enabled

  Scenario: Manifest contains hashes and pointers but no raw evidence content
    When I inspect the manifest
    Then each evidence artifact should have a SHA-256 hash
    And each evidence artifact should have a deterministic pointer
    And the manifest should not contain raw evidence snippets

  Scenario: Audit log references evidence by id and pointer only
    When I inspect the audit file
    Then each evidence reference should include "evidence_id"
    And each evidence reference should include "pointer"
    And the audit should not include raw evidence payloads

  Scenario: Replay requires the original evidence artifacts to be present locally
    Given an audit file from a hash-only run
    And the evidence artifacts are missing locally
    When I try to replay the audit
    Then the replay should fail with validation error
    And the error should mention "missing evidence artifact"
