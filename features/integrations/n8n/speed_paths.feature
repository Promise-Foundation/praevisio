@integration @n8n @praevisio @speed
Feature: Fast paths keep shipping velocity high while preserving safety
  As a product team
  I want governance to be fast and targeted
  So that we only do expensive checks when they matter

  Background:
    Given n8n can classify changes by paths, labels, or diff content:
      | classification_rule                         | impact |
      | changes under "infra/" or "auth/"           | high   |
      | changes under "docs/" only                  | low    |
      | changes touching LLM boundary module        | high   |
      | dependency bump only                        | medium |

  @skip_low_risk
  Scenario: Low-impact changes run a lightweight check and do not block
    Given a change is classified as "low"
    When n8n triggers governance
    Then n8n should run only a lightweight Praevisio promise set
    And the workflow should complete within 60 seconds
    And failing low-severity checks should notify but not block

  @focus_high_risk
  Scenario: High-impact changes run the full critical promise set
    Given a change is classified as "high"
    When n8n triggers governance
    Then n8n should run the full "critical_promises" set
    And any failure in high severity should block automatically
    And the output should include actionable next steps (ticket links or evidence to collect)
