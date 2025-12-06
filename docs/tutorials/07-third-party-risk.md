#+TITLE: Tutorial 7 – Third-Party Risk Management: Governing Code You Don’t Control
#+AUTHOR: Praevisio
#+OPTIONS: toc:3 num:t ^:nil

* What You'll Learn

In Tutorials 1–6, you focused on governing *your own* code and systems:
- Logging and observability
- Static analysis
- CI gating
- Red-teaming adversarial risks
- Prompt injection defense
- PII masking and privacy controls

But in modern systems, **your risk is increasingly determined by code you did not write**.

This is the domain of *Third-Party Risk Management (TPRM)*.

In this tutorial, you’ll learn how to:

- Model vendors as change-originating agents whose releases must be governed just like your own
- Create promises that apply specifically to vendors
- Require cryptographically signed “vendor evidence bundles” per release
- Automatically evaluate vendor updates at your receiving dock
- Block vendor updates whose evidence does not satisfy your NIST, HIPAA, PCI, or EU AI Act obligations
- Merge supply-chain attestations (SLSA, in-toto) with Praevisio’s higher-order promise layer
- Generate regulator-ready audit trails showing proof, not PDFs

By the end, you will treat vendor software as if it were *extension of your own CI pipeline*—with guarantees instead of trust.

This is the shift from “we rely on a SOC2 from last year” to “we verify every release.”

---

* Why This Matters: Your Weakest Link Is Now External

Most compliance failures in modern AI systems originate *outside* the organization:

- A vendor changes a logging format → breaks traceability → violates NIST PR.PT or EU AI Act Art. 12 logging requirements.
- A model hosting provider updates its container image → adds a dependency with a critical CVE → violates SOC2 CC7 or NIST PR.IP-12.
- A third-party LLM API changes behavior → fails safety filters → violates your own documented risk controls.

Traditional TPRM gives you:
- Annual questionnaires
- SOC2 PDFs
- Vendor attestation emails

None of these tell you whether *this specific release* of the vendor’s software satisfies *your* obligations.

Praevisio changes this by treating vendor deliveries as evidence-bearing artifacts—no different from your own builds.

---

* Regulatory Drivers

**NIST CSF 2.0 – Supply Chain Risk Management (ID.SC)**  
NIST explicitly requires continuous verification of third-party controls, not periodic attestation.

**NIST AI RMF – Measure & Manage**  
You must measure and manage *third-party contributions to AI risk*, including model version updates and data processors.

**EU AI Act – Art. 15, Art. 28, Annex VIII**  
You are liable for risks created by third-party components inside a high-risk AI system, *even if you did not develop them*.

**HIPAA**  
Business Associates must provide verifiable evidence that PHI is protected—contracts alone are insufficient.

**PCI-DSS**  
Third-party service providers must demonstrate compliance on every change impacting cardholder data environments.

The direction is clear:  
You can no longer say “our vendor assured us it was fine.”  
You must *prove* it.

---

* The Praevisio Model: Vendors as Promising Agents

In Praevisio, your systems have promises.  
Your developers provide evidence.  
Your CI gates enforce thresholds.

Vendors can participate in the exact same lifecycle.

**A vendor release is treated as:**
1. A *change*
2. Originating from an *external agent*
3. Subject to *your* promises
4. Required to provide *their own evidence bundle*
5. Evaluated by Praevisio at *your* receiving dock

If the vendor fails a critical promise, the update is blocked before entering your environment.

This is the difference between *trusting a vendor* and *verifying a vendor*.

---

* Anatomy of a Vendor Evidence Bundle

Vendor bundles contain the same elements as internal ones:

1. **Signed provenance**  
   - SLSA v1 or in-toto attestations  
   - Build environment, materials, build steps  
   - SHA-256 artifact signatures

2. **Vendor promises**  
   Examples:
   - “All PHI masking tests must pass”
   - “All outbound connections must be explicitly declared”
   - “Model fairness tests must exceed 0.90 min parity”
   - “Security scans show no HIGH or CRITICAL severity CVEs”

3. **Evidence**  
   - Procedural: tests from vendor CI  
   - Static analysis: dependency graphs, SBOM diffs  
   - Adversarial results: safety regression tests  
   - Configuration: container hardening, IAM checks  
   - Logs: dependency integrity, patch levels

4. **Framework mappings**  
   Mapped to *your* obligations:
   - NIST CSF functions  
   - SOC2 controls  
   - HIPAA Security Rule  
   - PCI-DSS v4  
   - EU AI Act Annex VIII requirements  

5. **Signatures & attestations**  
   - Artifact signatures  
   - Evidence signing key  
   - Optional timestamp authority (TSA)

The vendor bundle becomes your *canonical evidence* for that update.

---

* Creating a Vendor-Specific Promise Pack

Create a new file:

```yaml
id: tprm-vendor-update
version: 0.1.0
domain: /third_party/updates
statement: >
  All vendor-delivered software, models, or configurations must include a
  cryptographically signed evidence bundle tied to the specific release,
  demonstrating compliance with our security, privacy, and AI governance
  requirements. No vendor update may be deployed without satisfying these
  promises.

severity: high
critical: true

success_criteria:
  credence_threshold: 0.95
  confidence_threshold: 0.70
  evidence_types:
    - provenance
    - static_analysis
    - procedural
    - adversarial
    - privacy_check

parameters:
  require_slsa_level: 2
  require_sbom: true
  max_cve_severity: "medium"
  require_model_card: true
  require_privacy_evidence: true
  require_regression_tests: true
  vendor_signature_alg: "sha256-rsa"

metadata:
  regulatory_mapping:
    nist_csf: "ID.SC-1, ID.SC-4, PR.DS-1, PR.IP-12"
    soc2: "CC7 (change mgmt), CC6 (vendor mgmt)"
    hipaa: "164.308(b)(1) – BA controls"
    pci_dss: "12.8.2 – Vendor security verification"
    eu_ai_act: "Art. 15, Annex VIII – Third-party component governance"
```

This promise enforces:

- You cannot ingest a vendor artifact without provenance
- You cannot deploy it without evidence
- You cannot trust their “attestation PDF”—you need signed, machine-verifiable proof

---

* Setting Up a Vendor Receiving Dock

Add a Praevisio evaluation step to your vendor integration pipeline:

```bash
praevisio evaluate-vendor \
  --bundle vendor_release.bundle \
  --promises governance/promises/tprm-vendor-update.yaml \
  --fail-on-violation
```

Behind the scenes:

1. Praevisio verifies the signature chain  
2. Validates SLSA provenance  
3. Parses SBOM + vulnerability scan  
4. Gathers all evidence into a unified credence score  
5. Applies your thresholds  
6. Produces a vendor audit report

If any required evidence is missing → **blocked**.  
If CVEs exceed severity threshold → **blocked**.  
If fairness tests regressed → **blocked**.  
If privacy masking tests fail → **blocked**.

You do not deploy “trust.”  
You deploy *proof*.

---

* Example Failure Report

```
❌ Vendor Update Blocked – Insufficient Evidence

Bundle: bank-ml-model-v3.4.1.bundle
Credence: 0.61 (Threshold: 0.95)

Failures:
 - Missing SLSA provenance (expected level 2)
 - SBOM shows dependency 'pyyaml 5.1' with HIGH CVE-2020-14343
 - Fairness regression: disparate impact = 0.62 (min: 0.80)
 - Privacy tests missing (no PHI masking evidence submitted)

Deployment blocked per TPRM policy.
Please contact vendor for corrected evidence.
```

This is the kind of artifact regulators *love* because it is:
- Deterministic  
- Reproducible  
- Cryptographically verifiable  
- Tied to a single release  
- Mapped to governance obligations  

---

* Integrating Vendor Data into Your Evidence Bundles

When you later generate your own bundle:

```bash
praevisio bundle create --release internal-api:v4.1.0
```

Your bundle automatically includes:

- A reference to each vendor bundle used in this release
- Verification proofs
- Evidence lineage
- Framework mappings

This creates a **complete supply-chain evidence graph**, not a flat list of PDFs.

---

* Auditing: How This Changes the Conversation

Without Praevisio, vendors give you:
- PDFs  
- SOC2 reports  
- Annual questionnaires  
- Vague claims  

With Praevisio, you hand auditors:

1. **Vendor bundle for every update**  
2. **Proof of verification**  
3. **List of rejected vendor updates**  
4. **Mapping to each regulatory control**  

Auditor question:  
“Show me proof that your model vendor conforms to Annex VIII of the EU AI Act.”

Your answer:  
“Here are the last 12 signed vendor bundles, each tied to specific model versions, including fairness tests, PHI handling checks, SLSA provenance, and deployment integrity.”

They rarely see this level of rigor. It is extremely defensible.

---

* Summary

You now know how to:

- Define vendor promises  
- Require vendor evidence bundles  
- Verify vendor provenance, tests, and safety evidence  
- Block vendor updates automatically  
- Build regulator-ready third-party audit trails  

This closes the last major governance gap:  
**Your system is no longer only as strong as your weakest vendor.**

---

* Next Steps

In Tutorial 8, you’ll learn how to *fuse* internal and external evidence into a unified supply-chain risk model, enabling multi-party change control for high-risk systems.

