Feature: Run pre-commit hooks
  Scenario: Skip hooks when no files match pattern
    Given a repository with staged Python files
    And a hook configuration for pattern "*.js"
    When I run pre-commit hooks
    Then the hook should be skipped

