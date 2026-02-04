@security @rbac @audit_pack
Feature: Role-based access control for evidence and audit artifacts
  As a diligence admin
  I want roles to control who can view evidence vs reports
  So that sensitive data is not over-shared

  Background:
    Given users "analyst", "counsel", and "auditor"
    And RBAC is enabled
    And an evaluation run has produced artifacts

  Scenario: Analyst can view evidence and audit
    When "analyst" requests the evidence bundle
    Then access should be granted

  Scenario: Auditor can view signed report but not raw evidence
    When "auditor" requests raw evidence
    Then access should be denied
    And the audit should record an "rbac_denial" entry

  Scenario: Counsel can view redacted excerpts only
    When "counsel" requests evidence excerpts
    Then only redacted excerpts should be returned
    And the response should include a redaction summary
