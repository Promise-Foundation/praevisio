@integration @n8n @praevisio @governance
Feature: n8n triggers Praevisio governance checks on change events
  As a team building fast
  I want n8n to automatically run Praevisio on every meaningful change
  So that risky changes are blocked (or escalated) before they ship

  Background:
    Given an n8n instance with credentials to read the target repo or change payload
    And Praevisio is installed and runnable in the n8n execution environment
    And a Praevisio config file ".praevisio.yaml" exists in the target workspace
    And the n8n workflow includes nodes:
      | node_type          | purpose                                |
      | Trigger/Webhook    | receive change events                   |
      | Execute Command    | run "praevisio evaluate-commit"         |
      | Parse JSON         | parse Praevisio JSON output             |
      | Switch/IF          | route based on verdict/severity         |
      | Notifications      | Slack/Email/Teams message               |
      | Ticketing          | Jira/Linear task creation               |
      | Status/Checks API  | update PR check or deployment approval  |
      | Artifact Storage   | store run artifacts (manifest/audit)    |

  @happy_path @ci
  Scenario: GitHub PR update triggers a Praevisio run and records a PASS decision
    Given a pull request event "synchronize" occurs for repo "acme/app"
    And the change risk is classified as "high"
    When n8n checks out the PR ref into a workspace
    And n8n runs "praevisio evaluate-commit . --config .praevisio.yaml --json"
    Then the Praevisio output JSON should include "verdict" as "green"
    And the output should include "credence"
    And the output should include "details.run_id"
    And the output should include "details.manifest_path" and "details.manifest_sha256"
    And the output should include "details.audit_path" and "details.audit_sha256"
    And n8n should persist the manifest and audit artifacts under the run_id
    And n8n should set the PR status check to "success"
    And n8n should notify the channel "eng-governance" with a PASS summary

  @blocker @ci
  Scenario: High-risk change fails governance and is blocked
    Given a pull request event occurs for repo "acme/app"
    And the change risk is classified as "high"
    And Praevisio will return verdict "red" with credence "0.70"
    When n8n runs the Praevisio evaluation for the PR
    Then n8n should set the PR status check to "failure"
    And n8n should prevent merge by requiring the failing check
    And n8n should create a ticket "Governance blocker" assigned to the PR author
    And the ticket should include:
      | field          | required_content                                  |
      | run_id         | the Praevisio run id                              |
      | promise_id     | the evaluated promise id(s)                       |
      | failing_gates  | which gates failed (e.g., credence>=threshold)    |
      | evidence_refs  | pointers to evidence artifacts used               |
      | audit_pointer  | audit path + sha256                               |
      | manifest_hash  | manifest sha256                                    |
    And n8n should notify "eng-governance" with a BLOCKED message including reasons

  @fail_closed @ci
  Scenario: Evaluation error fails closed and escalates
    Given a pull request event occurs
    And Praevisio execution fails with a non-zero exit code
    When n8n attempts to run Praevisio
    Then n8n should set the PR status check to "failure"
    And the failure reason should be "governance_evaluation_error"
    And n8n should notify "eng-governance" with an escalation message
    And n8n should create a ticket for manual review labeled "fail-closed"

  @rate_limit @reliability
  Scenario: n8n deduplicates repeated events to avoid double-running Praevisio
    Given two identical webhook deliveries arrive for the same PR SHA within 60 seconds
    When n8n receives the second delivery
    Then n8n should detect it as a duplicate by event_id or (repo, pr, sha)
    And n8n should not run Praevisio twice for the same SHA
    And n8n should annotate the workflow run as "deduped"
