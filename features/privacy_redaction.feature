Feature: Privacy redaction at LLM boundary
  Background:
    Given a privacy redaction module

  Scenario: Redact email addresses
    When I redact "Contact john@example.com for details"
    Then the output should not contain "john@example.com"
    And the output should contain "[REDACTED_EMAIL]"

  Scenario: Redact phone numbers
    When I redact "Call me at 555-123-4567"
    Then the output should not contain "555-123-4567"
    And the output should contain "[REDACTED_PHONE]"

  Scenario: Redact multiple PII types
    When I redact "Email: test@example.com, Phone: 555-123-4567, SSN: 123-45-6789"
    Then the output should contain 3 redaction markers
