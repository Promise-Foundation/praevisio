@integration @n8n @praevisio @offline @privacy
Feature: n8n enforces safe execution modes (offline, redaction) when running Praevisio
  As an org handling sensitive diligence data
  I want automated governance runs to be safe by construction
  So that confidential information does not leak

  Background:
    Given n8n can run workflow jobs inside a restricted runtime
    And the Praevisio config can enable offline mode and redaction policy

  @offline_mode
  Scenario: Runs are executed with network egress disabled
    Given the workflow is marked "sensitive"
    When n8n executes Praevisio
    Then Praevisio should be invoked with offline mode enabled
    And if any outbound network call is attempted the run should fail
    And the failure should be treated as "fail-closed"

  @redaction
  Scenario: Notifications and stored artifacts do not leak secrets
    Given evidence contains sensitive tokens or PII
    When Praevisio produces outputs
    And n8n posts summaries to Slack and stores artifacts
    Then the Slack message should contain redaction markers instead of raw secrets
    And the stored decision record should not contain raw sensitive payloads
    And the run should include a redaction summary in its audit trail
