@abductio @library @mismatch
Feature: Hypothesis library versioning and mismatch artifacts
  As a diligence user
  I want hypothesis libraries versioned and mismatch reported explicitly
  So that best-of-bad-set failures are avoided

  Background:
    Given a hypothesis library "ip_risks_v1"
    And a run uses that library

  Scenario: Run records library version and checksum
    When I run evaluation
    Then the manifest should include "hypothesis_library_id" as "ip_risks_v1"
    And it should include a library checksum

  Scenario: Low-fit library emits mismatch anomaly and raises residual mass
    Given applicability fit is low across all roots
    When I run evaluation
    Then the report should include anomaly "library_mismatch"
    And the credence should allocate at least "min_residual_mass" to "NOA"
