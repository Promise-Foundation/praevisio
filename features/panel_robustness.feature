@abductio @panel @robustness
Feature: Multi-assessor evaluation aggregates credence and confidence deterministically
  As a diligence lead
  I want multiple assessors to score the same obligations
  So that results are more robust and less biased

  Background:
    Given two assessors "A1" and "A2"
    And panel mode is enabled
    And the same evidence bundle is used for both

  Scenario: Each assessor produces a separate signed assessment
    When both assessors run evaluation
    Then there should be two assessment artifacts
    And each should be signed and hash-chained

  Scenario: Aggregation is deterministic and auditable
    When I run "praevisio aggregate --panel"
    Then the aggregated credence vector should be produced
    And the audit should include the aggregation rule and inputs hashes

  Scenario: Large assessor disagreement triggers an anomaly
    Given assessors disagree beyond threshold on a slot
    When I aggregate panel results
    Then the report should include an anomaly "assessor_disagreement"
    And the anomaly should include an operator action
