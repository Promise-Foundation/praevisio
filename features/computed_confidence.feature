@governance @decision @risk
Feature: Decision derives impact, likelihood, and confidence from evidence and policy
  As a diligence lead
  I want notification fields derived from rules
  So that severity language is consistent and defensible

  Scenario: Impact derives from severity of violated promises
    Given a violated promise with severity "high"
    When a decision is produced
    Then notification.impact should be "high"

  Scenario: Likelihood derives from credence bands
    Given a violated promise with credence 0.97
    When a decision is produced
    Then notification.likelihood should be "near_certain"
    And notification.confidence should be "high"

  Scenario: Low credence yields lower likelihood or low confidence
    Given a violated promise with credence 0.55
    When a decision is produced
    Then notification.likelihood should be "possible" or "likely"
    And notification.confidence should be "low" or "medium"

  Scenario: Tooling error yields high uncertainty
    Given a promise verdict is "error"
    When a decision is produced
    Then notification.confidence should be "low"
    And the decision should include a reason code "tooling_error"
