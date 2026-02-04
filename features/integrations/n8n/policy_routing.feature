@integration @n8n @praevisio @policy
Feature: Policy routing in n8n based on severity, applicability, and governance verdict
  As a governance engineer
  I want n8n routing rules to be explicit and testable
  So that "build fast" does not override "don’t break things"

  Background:
    Given a routing policy configured in n8n:
      | condition                                         | action                         |
      | verdict=green                                      | allow                          |
      | verdict=red AND severity=high                      | block + ticket + notify        |
      | verdict=red AND severity=medium                    | ticket + notify                |
      | verdict=red AND severity=low                       | notify only                    |
      | verdict=error                                      | fail-closed + escalate         |
      | applicable=false OR verdict="n/a"                  | record + allow with annotation |

  @applicability
  Scenario: Not-applicable evaluation is allowed but recorded
    Given Praevisio output has "verdict" as "n/a"
    And the output details indicate "applicable" is false
    When n8n applies routing policy
    Then n8n should allow the change to proceed
    And n8n should post a message including "not_applicable"
    And n8n should store the run artifacts for auditability

  @medium_severity
  Scenario: Medium-severity failure creates follow-up work but does not block merge
    Given Praevisio output has "verdict" as "red"
    And the routed severity is "medium"
    When n8n applies routing policy
    Then n8n should not block the merge
    But n8n should create a ticket with due date within 7 days
    And the ticket should include the run_id and audit/manifest hashes
    And n8n should notify "eng-governance" with "action_required"
