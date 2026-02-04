@integration @n8n @praevisio @multi_promise
Feature: n8n runs multiple Praevisio promises and aggregates into one governance decision
  As a team shipping changes across multiple risk domains
  I want one clear decision derived from multiple checks
  So that approvals are consistent and explainable

  Background:
    Given a promise set "critical_promises" includes:
      | promise_id                     | severity |
      | llm-input-logging              | high     |
      | llm-privacy-redaction          | high     |
      | llm-prompt-injection-defense   | high     |
      | third-party-risk-reviewed      | medium   |
    And n8n can invoke Praevisio once per promise_id
    And n8n can store multiple run_ids under a single "decision_id"

  @aggregate_pass
  Scenario: All critical promises pass => decision is ALLOW
    When n8n runs Praevisio for each promise in "critical_promises"
    And each result has verdict "green"
    Then the aggregated decision should be "allow"
    And n8n should write a "decision_record.json" containing:
      | field                 | requirement                                  |
      | decision_id           | stable unique id                              |
      | timestamp             | decision time                                 |
      | inputs                | list of (promise_id, run_id, verdict, credence)|
      | policy_version        | the routing policy version                    |
      | allow_reason          | "all_critical_promises_passed"                |
      | artifact_pointers     | links/pointers to each run folder             |

  @aggregate_fail
  Scenario: Any high-severity promise fails => decision is BLOCK
    Given one promise "llm-input-logging" returns verdict "red"
    And its severity is "high"
    When n8n aggregates results
    Then the aggregated decision should be "block"
    And the decision record should list "blocking_promises" including "llm-input-logging"
    And n8n should set the PR status check to "failure"
    And n8n should notify with the top 3 reasons across blocking promises

  @partial_fail
  Scenario: Only medium-severity promise fails => decision is ESCALATE
    Given all high severity promises are "green"
    And the medium severity promise "third-party-risk-reviewed" is "red"
    When n8n aggregates results
    Then the aggregated decision should be "escalate"
    And n8n should create a ticket for vendor review
    And n8n should allow merge only if the change scope is not "vendor_addition"
    And n8n should annotate the PR with "conditional_approval"
