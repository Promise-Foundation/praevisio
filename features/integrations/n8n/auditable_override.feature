@integration @n8n @praevisio @override @high_value
Feature: Override workflow creates an auditable override artifact for red decisions
  As a governance lead
  I want red decisions to require explicit approval with a signed override artifact
  So that exceptions are controlled, attributable, and reviewable

  Background:
    Given an n8n workflow "praevisio_override" is enabled
    And the workflow can create approval tasks in "Jira" or "Slack"
    And the workflow can store artifacts in immutable storage
    And Praevisio emits a decision record for each run

  @requires_approval
  Scenario: Red decision triggers an approval task and blocks deployment
    Given a Praevisio run completed with verdict "red"
    And the decision record indicates "impact: high" and "likelihood: near_certain"
    When n8n receives the "praevisio.decision.created" event
    Then n8n should create an approval task with required approver role "governance_admin"
    And n8n should block the downstream deploy job
    And n8n should attach the decision record, audit hash, and manifest hash to the approval task

  @approved_override
  Scenario: Approval produces an override artifact and unblocks deployment
    Given a Praevisio decision is "red" for run "RUN123"
    And an approver "alice" approves with rationale "time-critical hotfix"
    And an expiry is set to "7 days"
    When n8n records the override
    Then n8n should create an "override.json" artifact containing:
      | field            |
      | run_id           |
      | decision_id      |
      | approved_by      |
      | approved_at      |
      | rationale        |
      | expiry           |
      | compensating_controls |
    And the override artifact should be hash-chained and stored immutably
    And the override artifact should reference the decision record hash
    And n8n should unblock the downstream deploy job
    And the system should mark the deployment as "override_applied"

  @denied_override
  Scenario: Denial keeps deployment blocked and escalates
    Given a Praevisio decision is "red" for run "RUN124"
    When the approval task is denied by "alice"
    Then n8n should keep the downstream deploy job blocked
    And n8n should notify the on-call channel
    And n8n should record a denial event linked to the decision record

