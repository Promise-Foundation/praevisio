@abductio @voi @ux
Feature: Weakest-slot drilldown suggests next best evidence to collect
  As a diligence user
  I want the system to explain what is bottlenecking confidence
  So that I can collect the highest-value missing evidence

  Background:
    Given an evaluation run has completed

  Scenario: Report shows weakest slot per root
    When I view the report
    Then each root should include "weakest_slot"
    And it should include the slot name, p, k, and evidence IDs used

  Scenario: System recommends evidence actions tied to the weakest slot
    When I request "next_actions"
    Then the output should list suggested evidence collections
    And each action should include an expected impact rationale
    And the audit should record the VOI-lite scoring inputs
