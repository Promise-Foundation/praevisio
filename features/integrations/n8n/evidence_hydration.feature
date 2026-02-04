@integration @n8n @praevisio @evidence @high_value
Feature: Evidence hydration imports external evidence before a Praevisio run
  As a diligence provider
  I want n8n to fetch external evidence and register it in the run manifest
  So that Praevisio decisions incorporate signals beyond the repository

  Background:
    Given an n8n workflow "praevisio_evidence_hydration" is enabled
    And the workflow can fetch evidence from "S3", "GitHub Releases", or "VDR exports"
    And the workflow can write files under ".praevisio/runs/<run_id>/evidence/"
    And Praevisio is configured to reference hydrated evidence by deterministic pointers

  @happy_path
  Scenario: Hydrate SBOM + vuln scan into the run and record provenance
    Given a run is about to start for repository "acme/app" at commit "abc123"
    And an SBOM artifact exists at "s3://acme-security/sbom/acme-app-abc123.json"
    And a vulnerability scan exists at "s3://acme-security/scans/acme-app-abc123.sarif"
    When n8n downloads the SBOM and vuln scan into the run evidence directory
    And n8n writes a provenance record for each evidence item including source URI and fetched_at timestamp
    And n8n runs "praevisio evaluate-commit . --config .praevisio.yaml --json"
    Then the Praevisio manifest should list the hydrated evidence artifacts
    And each hydrated artifact should include a SHA-256 hash
    And the audit should reference hydrated evidence by id and pointer

  @missing_external_evidence
  Scenario: Missing external evidence yields an explicit anomaly and residual increase
    Given a run is about to start for repository "acme/app" at commit "def456"
    And the expected SBOM artifact is not available
    When n8n starts the Praevisio run anyway
    Then the report should include an anomaly "missing_external_evidence"
    And the anomaly should include which evidence URI was missing
    And the decision record should include residual mass allocated to "UND"

  @tamper_detection
  Scenario: Evidence tampering after hydration is detected by hash mismatch
    Given n8n hydrated an SBOM into the run directory
    And the SBOM hash was recorded in the manifest
    When the SBOM file content is modified after hydration
    And the run is replayed or verified
    Then verification should fail
    And the output should mention "evidence hash mismatch"
