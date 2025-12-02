Feature: Promise management via application service
  As a developer
  I want to register compliance promises
  So that I can verify behavior pre-deployment

  Scenario: Register a new promise
    Given an in-memory promise repository
    And a promise service
    When I register a promise with id "llm-input-logging-v1" and statement "All LLM API calls log input prompts"
    Then the returned promise has id "llm-input-logging-v1"
    And the returned promise has statement "All LLM API calls log input prompts"

