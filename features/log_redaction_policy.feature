@security @privacy @redaction
Feature: Redaction policy applies to all outputs and artifacts
  As a diligence user
  I want redaction applied everywhere Praevisio emits text
  So that secrets do not leak into logs, reports, or artifacts

  Background:
    Given a redaction policy configured in ".praevisio.yaml"
    And the policy includes patterns for emails, phone numbers, and secrets

  Scenario: CLI output is redacted
    When I run an evaluation that processes sensitive text "Contact john@example.com and token=SECRET123"
    Then the CLI output should not contain "john@example.com"
    And the CLI output should not contain "SECRET123"
    And the CLI output should contain redaction markers

  Scenario: Audit artifacts are redacted
    When I run an evaluation that processes sensitive text "token=SECRET123"
    Then the audit file should not contain "SECRET123"
    And the decision file should not contain "SECRET123"

  Scenario: Redaction actions are auditable
    When I run an evaluation
    Then the audit file should include a "redaction_summary"
    And the summary should include counts per redaction type
