@audit @export @bundle
Feature: Export a portable audit pack with verification tooling
  As a diligence user
  I want to export a sealed bundle for third parties
  So that auditors can verify integrity offline

  Background:
    Given an evaluation run completed with report signing enabled

  Scenario: Export produces a single bundle with manifest + signatures
    When I run "praevisio export --run RUN123 --out auditpack.zip"
    Then the bundle should include "manifest.json"
    And it should include "audit.jsonl"
    And it should include "report.pdf" or "report.json"
    And it should include signature files

  Scenario: Verify checks hash chain, signatures, and evidence hashes
    When I run "praevisio verify auditpack.zip"
    Then bundle verification should succeed
    And it should report "integrity_ok"

  Scenario: Tampering causes verification failure
    Given I modify one file in "auditpack.zip"
    When I run "praevisio verify auditpack.zip"
    Then bundle verification should fail
    And the output should mention which integrity check failed
