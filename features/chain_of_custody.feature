@security @audit @chain_of_custody
Feature: Evidence chain-of-custody records every access and transformation
  As a compliance officer
  I want evidence access and transformations logged
  So that audits show who accessed what and when

  Background:
    Given an evidence store with at least one document
    And chain-of-custody logging is enabled

  Scenario: Reading evidence emits an access log entry
    When a component reads evidence "E123"
    Then the audit should include an "evidence_access" entry for "E123"
    And the entry should include "actor", "timestamp", and "purpose"

  Scenario: Transforming evidence records inputs and outputs
    When I run a transformation "ocr" on evidence "E123"
    Then the audit should include an "evidence_transform" entry
    And it should include "input_hash" and "output_hash"
    And it should include the transformation tool version
