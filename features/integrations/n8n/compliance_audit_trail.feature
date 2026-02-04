@integration @n8n @praevisio @compliance @retention @high_value
Feature: Compliance audit trail archives run artifacts immutably with retention rules
  As a compliance officer
  I want Praevisio run artifacts archived with retention controls
  So that audits can verify integrity and data minimization requirements are met

  Background:
    Given an n8n workflow "praevisio_compliance_archive" is enabled
    And the workflow can write to WORM/immutable storage
    And the organization defines retention classes "standard" and "hash_only"
    And Praevisio produces a manifest with SHA-256 hashes for artifacts

  @standard_retention
  Scenario: Standard retention stores full audit pack for SOC2 evidence
    Given a Praevisio run completes for repository "acme/app"
    And the configured retention class is "standard"
    When n8n archives the run artifacts
    Then the archive should include the audit log and manifest
    And the archive should include the exported audit pack bundle
    And the archive should record retention policy "soc2_1_year"
    And a periodic verification job should be scheduled

  @hash_only_retention
  Scenario: Hash-only retention stores pointers and hashes for GDPR-minimizing environments
    Given a Praevisio run completes for repository "acme/app"
    And the configured retention class is "hash_only"
    When n8n archives the run artifacts
    Then the archive should not contain raw evidence payloads
    And the archive should contain hashes and deterministic pointers only
    And the decision record should state "hash_only_evidence_retention: enabled"

  @periodic_verification
  Scenario: Periodic verification detects integrity drift in archived artifacts
    Given a run archive exists for "RUN200"
    When n8n performs scheduled verification
    Then verification should recompute hashes and validate signatures
    And the result should be recorded as "integrity_ok" or "integrity_failed"
    And failures should create an incident ticket with severity "high"
