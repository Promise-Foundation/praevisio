
@integration @n8n @praevisio @policy @high_value
Feature: Policy change pipeline performs dry-run impact analysis and requires approval
  As a governance engineer
  I want policy changes to be evaluated with a dry-run impact report
  So that tightening or loosening rules does not silently increase risk or break delivery

  Background:
    Given an n8n workflow "praevisio_policy_change" is enabled
    And policy files live under "governance/promises/" and ".praevisio.yaml"
    And a set of representative repositories is configured for impact analysis
    And the workflow can create a change ticket and request approval

  @tightening_requires_approval
  Scenario: Tightening a critical threshold requires explicit approval
    Given a pull request changes "governance/promises/llm-input-logging.yaml"
    And the credence_threshold is increased from 0.95 to 0.98
    When n8n detects a "policy file changed" event
    And n8n runs dry-run evaluations across the representative repositories
    Then n8n should produce a "policy_impact_report.json" containing pass/fail deltas per repo
    And the report should summarize "new failures introduced"
    And n8n should open a change ticket requiring approval by "governance_admin"
    And the PR should be blocked until approval is granted

  @loosening_requires_risk_acceptance
  Scenario: Loosening a critical policy requires risk acceptance metadata
    Given a pull request changes a critical promise threshold downward
    When n8n runs policy impact analysis
    Then the workflow should require a risk acceptance statement
    And the workflow should record who accepted the risk and why
    And the decision record should reference the policy change ticket id

  @no_behavior_change
  Scenario: Policy refactor with no effective change is auto-approved
    Given a pull request changes formatting and comments only in policy files
    When n8n computes the effective policy diff
    Then the workflow should mark the policy change as "no_effective_change"
    And the PR should not be blocked by policy approval
