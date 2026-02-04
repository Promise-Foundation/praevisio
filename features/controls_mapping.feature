@compliance @controls @mapping
Feature: Map promises and evidence to compliance controls
  As a governance engineer
  I want every promise to map to external control frameworks
  So that compliance reporting is automated

  Background:
    Given a promise "llm-input-logging"
    And the promise is mapped to controls "EU_AI_ACT_ART12" and "SOC2_CC7"
    And an evaluation run has completed

  Scenario: Report includes control coverage and evidence links
    When I generate the compliance report
    Then the report should include a "controls_coverage" section
    And it should list each mapped control with pass/fail
    And each control should link to evidence IDs and audit steps

  Scenario: Missing mappings produce a compliance gap anomaly
    Given a promise without control mappings
    When I generate the compliance report
    Then the report should include an anomaly "missing_control_mapping"
    And the anomaly should include an operator action
