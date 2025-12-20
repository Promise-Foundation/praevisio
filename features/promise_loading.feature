Feature: Load promise definitions from YAML
  Scenario: Load existing promise
    Given a promise file "llm-input-logging.yaml" exists
    When I load promise "llm-input-logging"
    Then the promise should have id "llm-input-logging"
    And the promise statement should match the YAML file

  Scenario: Fail gracefully when promise file missing
    When I try to load promise "nonexistent-promise"
    Then a FileNotFoundError should be raised
    And the error should mention "governance/promises/nonexistent-promise.yaml"
