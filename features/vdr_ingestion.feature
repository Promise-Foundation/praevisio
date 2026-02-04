@diligence @vdr @ingestion
Feature: Virtual data room ingestion with immutable provenance
  As a diligence user
  I want to import documents from a VDR with provenance metadata
  So that every claim is traceable to a source

  Background:
    Given a VDR export directory "vdr_export/"
    And ingestion is enabled

  Scenario: Ingested documents get stable evidence IDs and hashes
    When I run "praevisio ingest vdr_export/ --into evidence/"
    Then each ingested document should have an "evidence_id"
    And each should have a SHA-256 hash recorded in the manifest
    And the manifest should include "source" as "VDR_IMPORT"

  Scenario: Provenance includes original path and timestamps
    When I inspect the manifest
    Then each evidence artifact should include "original_path"
    And each artifact should include "ingested_at"
