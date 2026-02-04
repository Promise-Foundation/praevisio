@abductio @adversarial @defeaters
Feature: Red-team mode challenges each root with strongest defeaters
  As a diligence lead
  I want adversarial challenges recorded per hypothesis
  So that overconfidence is reduced and defeaters are explicit

  Background:
    Given red-team mode is enabled
    And an evaluation run is in progress

  Scenario: Each root must record at least one defeater
    When I run evaluation
    Then each root should include a "defeaters" field
    And the field should reference evidence IDs or explicitly mark "underdetermined"

  Scenario: High confidence without defeaters triggers anomaly
    Given a root has confidence above threshold
    And it has no recorded defeaters
    When the report is generated
    Then the report should include anomaly "missing_defeaters"
    And the anomaly should include an operator action
