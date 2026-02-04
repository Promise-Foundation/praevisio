@integration @n8n @praevisio @governance @high_value
Feature: Repo/PR gatekeeper blocks risky changes and explains why
  As a governance engineer
  I want n8n to run Praevisio on PRs and set a required status check
  So that teams can ship fast while preventing high-risk regressions

  Background:
    Given an n8n workflow "praevisio_pr_gatekeeper" is enabled
    And a Praevisio project config exists at ".praevisio.yaml"
    And the workflow has access to run "praevisio ci-gate" inside CI
    And the workflow can post PR comments and set commit statuses

  @happy_path
  Scenario: PR passes when all required promises meet threshold
    Given a pull request "PR-101" is opened against "main"
    And the workflow receives a "pull_request.opened" webhook for "PR-101"
    When n8n checks out the PR head commit
    And n8n runs "praevisio ci-gate . --severity high --fail-on-violation --output logs/ci-gate-report.json"
    Then the command should exit with code 0
    And n8n should set the commit status "praevisio/gate" to "success"
    And n8n should post a PR comment containing "✅ GATE PASSED"
    And the PR comment should include the run id and manifest hash

  @violation
  Scenario: PR is blocked when a critical/high promise fails
    Given a pull request "PR-102" is opened against "main"
    And the workflow receives a "pull_request.synchronize" webhook for "PR-102"
    And the evaluation credence for promise "llm-input-logging" is 0.70
    When n8n runs "praevisio ci-gate . --severity high --fail-on-violation --output logs/ci-gate-report.json"
    Then the command should exit with code 1
    And n8n should set the commit status "praevisio/gate" to "failure"
    And n8n should post a PR comment containing "❌ GATE FAILED"
    And the PR comment should include:
      | field              |
      | failed_promise_id   |
      | credence            |
      | threshold           |
      | audit_path          |
      | audit_sha256        |
      | manifest_sha256     |

  @error
  Scenario: PR is blocked when Praevisio evaluation errors
    Given a pull request "PR-103" is opened against "main"
    And the workflow receives a "pull_request.opened" webhook for "PR-103"
    And the Praevisio promise file is missing
    When n8n runs "praevisio ci-gate . --severity high --fail-on-violation --output logs/ci-gate-report.json"
    Then the command should exit with code 1
    And n8n should set the commit status "praevisio/gate" to "error"
    And n8n should post a PR comment containing "❌ Evaluation error"
    And the PR comment should include an operator action "fix_missing_promise_or_config"

  @artifact_hand_off
  Scenario: Gate publishes a portable audit pack link for reviewers
    Given a pull request "PR-104" is opened against "main"
    When n8n runs the Praevisio gate successfully
    Then n8n should upload the run artifacts to an artifact store
    And n8n should include a link to the uploaded audit bundle in the PR comment
    And the link text should include "audit bundle"
