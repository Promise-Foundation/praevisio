@integration @n8n @praevisio @artifacts @audit
Feature: n8n stores and links Praevisio run artifacts for replay, verification, and evidence review
  As an auditor or diligence user
  I want every automated governance outcome to be reproducible
  So that decisions can be verified after the fact

  Background:
    Given n8n has an artifact storage location "governance_runs/"
    And each workflow execution creates a folder keyed by "run_id"
    And Praevisio produces:
      | artifact         | requirement                               |
      | manifest.json    | includes sha256 for each evidence artifact |
      | audit.json       | reproducible audit trace                   |
      | evidence/*       | collected evidence JSONs                   |

  @retention
  Scenario: Store artifacts with an immutable pointer and retention policy
    Given a Praevisio run completes with run_id "RUN123"
    When n8n stores artifacts for RUN123
    Then the storage path should be "governance_runs/RUN123/"
    And n8n should store "manifest.json" and "audit.json"
    And n8n should store evidence files referenced by the manifest
    And n8n should record a retention class "standard" or "hash-only"
    And n8n should expose a stable URL or pointer to the run folder

  @replay
  Scenario: Replay can be triggered from n8n to reproduce results
    Given a stored run folder exists for run_id "RUN123"
    When n8n runs "praevisio replay-audit governance_runs/RUN123/audit.json --json"
    Then replay output should include a reconstructed ledger
    And the replayed credence for the promise should equal the original credence within tolerance 0.0001
    And n8n should mark the run as "replay_verified"

  @tamper_detection
  Scenario: Artifact tampering is detected and escalated
    Given a stored run folder exists
    And "manifest.json" sha256 does not match the stored manifest hash record
    When n8n performs an integrity check
    Then n8n should flag the run as "integrity_failed"
    And n8n should notify "security-governance" immediately
    And n8n should block any downstream approvals that reference that run
