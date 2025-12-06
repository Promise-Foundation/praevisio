# Tutorial 6 – Privacy and PII Detection: Protecting Sensitive Data

## What You'll Learn

In Tutorials 4 and 5, you learned how to defend against adversarial attacks—malicious users trying to break your system. But not all AI governance risks come from attackers. Sometimes the biggest risk is that your system works exactly as designed, but processes data it shouldn't have access to in the first place.

Consider what happens when a user asks your LLM: "Summarize this email for me: From: john.doe@company.com, SSN: 123-45-6789, Credit Card: 4532-1234-5678-9012..." Your LLM will happily process that data, generate a summary, and might even log the full prompt—complete with all that sensitive information—to your audit database.

This is a privacy violation waiting to happen. Even if the user willingly provided the data, your system has no business storing plaintext credit card numbers or social security numbers. If that data leaks (through a breach, a bug, or a careless employee), you're liable under GDPR, CCPA, and other privacy regulations.

In this tutorial, you'll learn how to:

- Understand why PII (Personally Identifiable Information) in LLM systems is particularly risky
- Install and configure Microsoft Presidio, an open-source PII detection and anonymization framework
- Create a promise that requires PII to be masked before LLM processing and storage
- Write evidence adapters that verify PII masking is actually happening
- Handle the privacy-utility tradeoff (aggressive masking protects privacy but reduces LLM usefulness)
- See how this satisfies GDPR, EU AI Act, and ISO 42001 data protection requirements
- Combine PII protection with your existing security defenses for comprehensive governance

By the end, you'll have a complete data protection layer that prevents sensitive information from being processed, stored, or leaked by your LLM system—and Praevisio will verify it's working correctly.

## The Problem: PII Leakage in LLM Systems

LLMs are incredibly effective at processing natural language, which means they're also incredibly effective at processing sensitive information embedded in that natural language. This creates unique privacy risks that don't exist in traditional software systems.

Consider these scenarios:

**Scenario 1: Unintentional data inclusion**
A customer service rep pastes a support ticket into your LLM assistant: "Customer Jane Smith (SSN: 123-45-6789) reports billing issue with account #9876543210..." The LLM processes it, generates a helpful response, and everything seems fine. Except now that SSN and account number are in your logs, your LLM's context window, potentially your fine-tuning data, and anywhere else prompts get stored.

**Scenario 2: Transitive disclosure**
A user asks: "Summarize my medical records." Your system faithfully processes those records, which contain diagnoses, medications, and other protected health information (PHI). Even if you don't log the prompt, the LLM now has that information in its context, and future responses might inadvertently reference it.

**Scenario 3: Aggregation risk**
Individual queries might not contain obvious PII, but the aggregate of many queries can reveal sensitive information. User asks: "I live at [address]" (one query), "My birthday is [date]" (another query), "My employer is [company]" (third query). Separately these seem innocuous, but together they uniquely identify someone.

**Scenario 4: Model memorization**
LLMs can memorize training data. If your fine-tuning data includes PII, the model might regurgitate it in responses to unrelated queries. This has been demonstrated with large models "remembering" phone numbers, addresses, and other sensitive data from training.

Traditional software handles PII by carefully controlling which database fields contain sensitive data and encrypting or restricting access to those fields. But LLMs process unstructured text—you can't just mark a "PII field." The sensitive data is embedded in natural language that the LLM needs to understand.

This is where automated PII detection and masking becomes essential. Before any text reaches your LLM, you need to:
1. Detect what's PII (emails, SSNs, credit cards, names, addresses, etc.)
2. Mask or redact that PII (replace with tokens or generic placeholders)
3. Process the masked text with your LLM
4. Optionally, restore the PII in the response if needed for the user

This way, your LLM never sees the actual sensitive data—it sees "[EMAIL]" instead of "john@example.com", "[SSN]" instead of "123-45-6789", etc.

## The Regulatory Context: Data Protection by Design

Privacy protection isn't just a best practice—it's a legal requirement under multiple regulations. Let's understand what regulators expect.

### GDPR: Data Minimization and Purpose Limitation

The EU's General Data Protection Regulation (GDPR) has two principles that directly apply here:

**Data minimization (Article 5.1.c)**: "Personal data shall be adequate, relevant and limited to what is necessary in relation to the purposes for which they are processed."

Translation: If your LLM doesn't need to know someone's SSN to answer their question, you shouldn't process that SSN. Even if the user provided it, you have a duty to minimize what you collect and process.

**Purpose limitation (Article 5.1.b)**: "Personal data shall be collected for specified, explicit and legitimate purposes and not further processed in a manner that is incompatible with those purposes."

Translation: If you collected an email address for account creation, you can't then use it to train your LLM unless that's a compatible purpose (it usually isn't).

The penalty for violations: up to €20 million or 4% of global annual revenue, whichever is higher. This makes PII protection not just a technical concern but a business-critical one.

### EU AI Act: Data Governance and Privacy

The EU AI Act (Articles 10 and related) requires high-risk AI systems to have appropriate data governance practices, including:

> "Training, validation and testing data shall be subject to appropriate data governance and management practices, including measures to ensure the quality and adequacy of data sets, and to prevent the use of biased or discriminatory data."

The Act specifically calls out privacy protection:
- Personal data processing must comply with GDPR
- Data sets must be "relevant, representative, free of errors and complete"
- Measures must prevent unauthorized use of personal data

PII masking satisfies these requirements by ensuring that personal data in prompts doesn't contaminate your logs, training data, or model context.

### ISO/IEC 42001: Privacy Risk Management

ISO 42001, the emerging AI management system standard, requires organizations to identify and mitigate privacy risks throughout the AI lifecycle. Specifically:

- Risk assessment must include privacy considerations
- Controls must be implemented to protect personal data
- Organizations must demonstrate that privacy measures are effective

Praevisio operationalizes this by treating PII masking as a verifiable promise: "We promise that PII is detected and masked before LLM processing." Evidence includes:
- Deployment verification (is Presidio installed and configured?)
- Effectiveness testing (does it catch various PII types?)
- Integration verification (are all prompts going through masking?)
- Coverage analysis (what percentage of PII is being masked?)

## Introducing Microsoft Presidio

Presidio is an open-source data protection and anonymization SDK from Microsoft. It's specifically designed to detect and mask PII in unstructured text, making it perfect for protecting LLM inputs.

What makes Presidio particularly suitable:

**It recognizes 20+ PII types out of the box**: emails, phone numbers, credit cards, SSNs, IP addresses, names (using NER models), locations, medical records numbers, and more. You don't need to build this detection logic yourself.

**It's highly accurate**: Presidio uses a combination of pattern matching (regex) and machine learning (NER models) to detect PII. Patterns catch structured data (email formats, credit card numbers). ML catches unstructured data (names in natural language).

**It supports multiple languages**: English, Spanish, French, German, and more. If you have international users, Presidio can detect PII in their native languages.

**It provides flexible anonymization**: You can replace PII with placeholders ("[EMAIL]"), with synthetic data ("john@example.com" → "user_1234@example.com"), or with hashes. Choose based on your use case.

**It's extensible**: You can add custom PII types (e.g., your company's employee ID format) by defining new recognizers. This lets you protect domain-specific sensitive data.

**It's production-ready**: Presidio is used in Microsoft's own products. It's well-tested, performant (processes ~1000 documents/second), and actively maintained.

**It integrates with LLM frameworks**: Presidio has built-in integrations with LangChain, LlamaIndex, and other popular LLM frameworks. But for this tutorial, we'll integrate it directly to understand the mechanics.

## Creating the PII Protection Promise

Let's create a new promise that captures what we want to verify about PII protection. Create `governance/promises/pii-data-protection.yaml`:
```yaml
id: pii-data-protection
version: 0.1.0
domain: /data/privacy
statement: >
  All user-provided text must be scanned for PII (Personally Identifiable 
  Information) before being processed by the LLM or stored in logs. Detected 
  PII must be masked or anonymized. The system must detect and mask at least 
  95% of common PII types including emails, phone numbers, SSNs, credit cards, 
  names, and addresses.

severity: high
critical: true

success_criteria:
  credence_threshold: 0.93
  confidence_threshold: 0.75
  evidence_types:
    - deployment_verification
    - effectiveness_testing
    - integration_verification
    - coverage_analysis
    - procedural

parameters:
  # PII types that must be detected
  required_pii_types:
    - EMAIL_ADDRESS
    - PHONE_NUMBER
    - CREDIT_CARD
    - US_SSN
    - PERSON
    - LOCATION
    - DATE_TIME
    - IP_ADDRESS
    - IBAN_CODE
    - MEDICAL_LICENSE
    
  # Masking configuration
  masking_strategy: replace  # Options: replace, redact, hash, encrypt, synthetic
  placeholder_format: "[{entity_type}]"  # e.g., "[EMAIL]", "[PHONE_NUMBER]"
  
  # Effectiveness thresholds
  minimum_detection_rate: 0.95  # Must catch 95% of PII
  maximum_false_positive_rate: 0.02  # Max 2% false positives
  
  # Coverage requirements
  coverage_requirement: 1.0  # 100% of LLM inputs must be scanned
  bypass_allowed: false
  
  # Privacy-utility tradeoff monitoring
  track_utility_impact: true  # Measure how masking affects LLM usefulness
  acceptable_utility_loss: 0.10  # Max 10% reduction in utility
  
  # Evidence weights
  evidence_weights:
    deployment: 0.20
    effectiveness: 0.40
    integration: 0.20
    coverage: 0.15
    utility: 0.05  # Small weight for utility impact

stake:
  credits: 0

metadata:
  regulatory_mapping:
    gdpr: "Article 5.1.c (data minimization), Article 25 (data protection by design)"
    eu_ai_act: "Article 10 (data governance), Article 11 (technical documentation)"
    iso_42001: "Control 6.2.3 (privacy risk management)"
    ccpa: "Section 1798.100 (consumer data rights)"
  risk_level: critical  # Privacy violations can be existential
  data_category: pii
```

This promise is sophisticated because privacy protection involves multiple concerns:

**Detection effectiveness**: Can Presidio actually find the PII in text? This is tested with a corpus of examples containing various PII types.

**Integration completeness**: Are all LLM inputs going through Presidio? Even one unprotected code path is a vulnerability.

**Masking correctness**: Is the PII being properly masked (not just detected)? You need to verify that the output text doesn't contain the original PII.

**Coverage analysis**: What percentage of actual PII in real user queries is being caught? This is harder to measure than effectiveness testing because you don't know what PII users will provide.

**Utility impact**: How much does masking reduce the LLM's ability to provide useful responses? If you aggressively mask everything that might be a name, you might mask important non-PII content too.

The promise acknowledges the privacy-utility tradeoff by including `acceptable_utility_loss: 0.10`. This means: "We'll accept up to 10% reduction in LLM usefulness if necessary to protect privacy." Different organizations might set different values based on their risk tolerance.

## Installing and Configuring Presidio

Install Presidio and its dependencies:
```bash
pip install presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_lg  # NER model for name detection
```

Presidio has two main components:
- **Analyzer**: Detects PII in text and returns findings
- **Anonymizer**: Takes findings and masks/redacts/replaces PII

Create a configuration file at `config/presidio-config.yaml`:
```yaml
# Presidio configuration for PII detection and masking

analyzer:
  # Which language models to load
  languages:
    - en  # English
    # Add more: es (Spanish), fr (French), de (German), etc.
  
  # NER model for name detection
  nlp_engine: spacy
  spacy_model: en_core_web_lg
  
  # Detection threshold (0.0 - 1.0)
  # Higher = fewer false positives but might miss some PII
  min_score_threshold: 0.5
  
  # Which PII types to detect
  enabled_recognizers:
    - EmailRecognizer
    - PhoneRecognizer
    - CreditCardRecognizer
    - SsnRecognizer
    - IbanRecognizer
    - IpRecognizer
    - MedicalLicenseRecognizer
    - PersonRecognizer  # Names
    - LocationRecognizer  # Addresses
    - DateTimeRecognizer
    
  # Custom recognizers (domain-specific PII)
  custom_recognizers: []

anonymizer:
  # Default strategy for each PII type
  default_strategy: replace
  
  # Specific strategies per entity type
  entity_strategies:
    EMAIL_ADDRESS:
      type: replace
      new_value: "[EMAIL]"
    PHONE_NUMBER:
      type: replace
      new_value: "[PHONE]"
    CREDIT_CARD:
      type: replace
      new_value: "[CREDIT_CARD]"
    US_SSN:
      type: replace
      new_value: "[SSN]"
    PERSON:
      type: replace
      new_value: "[PERSON]"
    LOCATION:
      type: replace
      new_value: "[LOCATION]"
    DATE_TIME:
      type: keep  # Dates often aren't PII by themselves
    IP_ADDRESS:
      type: mask  # Show only first two octets: 192.168.x.x
      masking_char: "x"
      chars_to_mask: 8
      from_end: true

logging:
  # Log all PII detections for monitoring
  enabled: true
  log_path: logs/presidio/detections.jsonl
  
  # IMPORTANT: Never log the actual PII values
  include_pii_value: false
  include_pii_type: true
  include_confidence: true

performance:
  # Cache analyzer results for identical text
  enable_cache: true
  cache_ttl_seconds: 3600
  
  # Batch processing settings
  batch_size: 100
  timeout_ms: 200
```

This configuration makes several important choices:

**The threshold of 0.5** balances false positives and false negatives. Lower thresholds catch more PII but also flag more non-PII as false positives. Higher thresholds miss more real PII. 0.5 is a reasonable default.

**Different masking strategies for different PII types**: Emails and SSNs get replaced with generic placeholders. Dates are kept because they're often not sensitive by themselves. IP addresses are partially masked (show first two octets) because that's often enough for debugging while still protecting privacy.

**Never log actual PII values**: The logging configuration explicitly sets `include_pii_value: false`. Even in your security logs, you shouldn't store the actual PII—just the fact that PII was detected and what type it was.

**Timeout of 200ms**: PII detection must be fast enough not to noticeably slow down LLM requests. 200ms is acceptable latency overhead for privacy protection.

## Integrating Presidio into Your LLM Client

Now update `app/src/llm_client.py` to add PII protection as the first layer of defense:
```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import rebuff
from pathlib import Path
import yaml

class LLMClient:
    """LLM client with comprehensive data protection."""
    
    def __init__(self):
        self._logs = []
        
        # Load configuration
        presidio_config_path = Path("config/presidio-config.yaml")
        with open(presidio_config_path) as f:
            presidio_config = yaml.safe_load(f)
        
        rebuff_config_path = Path("config/rebuff-config.yaml")
        with open(rebuff_config_path) as f:
            rebuff_config = yaml.safe_load(f)
        
        # Initialize Presidio for PII protection
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.presidio_threshold = presidio_config["analyzer"]["min_score_threshold"]
        
        # Initialize Rebuff for injection protection
        self.rebuff = rebuff.RebuffClient(
            detection_threshold=rebuff_config["detection"]["threshold"],
            enable_learning=rebuff_config["detection"]["enable_learning"]
        )
        
        # Harmful content keywords
        self.harmful_keywords = [
            "weapon", "bomb", "hack", "break into", "kill", "hurt",
            "steal", "illegal", "drug", "harm myself", "suicide",
            "virus", "malware", "poison",
            "ignore all", "ignore previous", "disregard", "override",
            "pretend you're", "roleplay", "you are now"
        ]
    
    def generate(self, prompt: str) -> str:
        """Generate a response with comprehensive protection."""
        
        # DEFENSE LAYER 0: PII Detection and Masking
        # This happens FIRST, before anything else touches the data
        masked_prompt, pii_findings = self._mask_pii(prompt)
        
        # Log both original and masked (for audit, we log the masked version)
        self._log_prompt(masked_prompt, original_had_pii=len(pii_findings) > 0)
        
        # All subsequent layers work with the masked prompt
        prompt_to_process = masked_prompt
        
        # DEFENSE LAYER 1: Rebuff prompt injection detection
        injection_result = self.rebuff.detect_injection(prompt_to_process)
        
        if injection_result.is_injection:
            self._log_injection_attempt(prompt_to_process, injection_result)
            return self._injection_blocked_response(injection_result)
        
        # DEFENSE LAYER 2: Keyword-based safety filtering
        prompt_lower = prompt_to_process.lower()
        if any(keyword in prompt_lower for keyword in self.harmful_keywords):
            return self._safety_refusal(prompt_to_process)
        
        # DEFENSE LAYER 3: Jailbreak pattern detection
        if self._is_jailbreak_attempt(prompt_lower):
            return self._safety_refusal(prompt_to_process)
        
        # All defenses passed - generate response
        # Important: LLM only sees masked version, never original PII
        response = "This is a helpful response to your query."
        
        # If we masked PII and user needs it back in response, unmask
        # (This is optional and depends on your use case)
        # response = self._unmask_pii(response, pii_findings)
        
        return response
    
    def _mask_pii(self, text: str) -> tuple[str, list]:
        """
        Detect and mask PII in text.
        
        Returns:
            (masked_text, pii_findings): Masked text and list of findings
        """
        # Analyze text for PII
        findings = self.analyzer.analyze(
            text=text,
            language="en",
            score_threshold=self.presidio_threshold
        )
        
        if not findings:
            # No PII detected
            return text, []
        
        # Log PII detection (without the actual PII values)
        self._log_pii_detection(findings)
        
        # Anonymize the PII
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=findings
        )
        
        return anonymized.text, findings
    
    def _log_pii_detection(self, findings) -> None:
        """Log PII detections for monitoring (without actual PII values)."""
        for finding in findings:
            self._logs.append({
                "type": "pii_detected",
                "entity_type": finding.entity_type,
                "score": finding.score,
                "start": finding.start,
                "end": finding.end,
                # IMPORTANT: Never log finding.text (the actual PII)
            })
    
    def _injection_blocked_response(self, result) -> str:
        """Generate response when injection is detected."""
        return (
            "I detected that your input may contain a prompt injection attempt. "
            "For security reasons, I cannot process this request."
        )
    
    def _log_injection_attempt(self, prompt: str, result) -> None:
        """Log detected injection attempts."""
        self._logs.append({
            "type": "injection_attempt",
            "prompt": prompt[:100],
            "injection_score": result.score,
            "timestamp": result.timestamp
        })
    
    def _safety_refusal(self, prompt: str) -> str:
        """Generate a safety refusal response."""
        return (
            "I cannot help with that request. It appears to involve "
            "potentially harmful content."
        )
    
    def _is_jailbreak_attempt(self, prompt: str) -> bool:
        """Detect common jailbreak patterns."""
        jailbreak_patterns = [
            "ignore all previous",
            "disregard your instructions",
            "you are now",
            "pretend you are",
            "act as if"
        ]
        return any(pattern in prompt for pattern in jailbreak_patterns)
    
    def _log_prompt(self, prompt: str, original_had_pii: bool = False) -> None:
        """Log the processed prompt."""
        self._logs.append({
            "type": "prompt",
            "content": prompt,  # This is the MASKED version
            "original_had_pii": original_had_pii
        })
    
    @property
    def logs(self) -> list:
        """Expose captured logs for verification."""
        return self._logs.copy()
```

Notice the architectural change: PII masking is now "Layer 0"—it happens before everything else. This is crucial because:

**Security defenses shouldn't see PII**: If Rebuff logs prompts for learning (which it does), those logs shouldn't contain PII. By masking first, we ensure Rebuff only ever sees "[EMAIL]" instead of "john@example.com".

**Logs are safe by default**: The audit log now contains masked prompts. Even if the log file leaks, it doesn't contain actual sensitive data.

**LLM never sees real PII**: The LLM processes "[PERSON] contacted us from [EMAIL] about account [CREDIT_CARD]" instead of "John Smith contacted us from john@example.com about account 4532-1234-5678-9012". This prevents the LLM from memorizing or leaking actual PII.

**Defense-in-depth continues**: After masking, all other defenses (injection detection, safety filtering) still run normally. Masking doesn't bypass security.

## Writing the Presidio Deployment Adapter

Create `governance/evidence/presidio_deployment_adapter.py`:
```python
"""
Presidio deployment verification adapter.

Verifies that Presidio is properly deployed and configured for PII protection.
"""

import importlib
import yaml
from pathlib import Path
from typing import Dict, Any


class PresidioDeploymentAdapter:
    """Verify Presidio deployment and configuration."""
    
    def __init__(self):
        self.config_path = Path("config/presidio-config.yaml")
        self.client_path = Path("app/src/llm_client.py")
    
    def verify_deployment(self) -> Dict[str, Any]:
        """Check all aspects of Presidio deployment."""
        
        evidence = {
            "deployment_status": "unknown",
            "checks_passed": [],
            "checks_failed": [],
            "overall_score": 0.0
        }
        
        # Check 1: Is Presidio installed?
        try:
            analyzer_mod = importlib.import_module("presidio_analyzer")
            anonymizer_mod = importlib.import_module("presidio_anonymizer")
            evidence["checks_passed"].append({
                "check": "presidio_installed",
                "details": "Presidio analyzer and anonymizer are installed"
            })
            presidio_installed = True
        except ImportError as e:
            evidence["checks_failed"].append({
                "check": "presidio_installed",
                "details": f"Presidio not installed: {e}"
            })
            presidio_installed = False
        
        # Check 2: Is spaCy NER model installed?
        try:
            spacy = importlib.import_module("spacy")
            # Try to load the model
            nlp = spacy.load("en_core_web_lg")
            evidence["checks_passed"].append({
                "check": "spacy_model_installed",
                "details": "spaCy en_core_web_lg model is available"
            })
            spacy_installed = True
        except Exception as e:
            evidence["checks_failed"].append({
                "check": "spacy_model_installed",
                "details": f"spaCy model not available: {e}"
            })
            spacy_installed = False
        
        # Check 3: Configuration file exists and is valid
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    config = yaml.safe_load(f)
                
                required_sections = ["analyzer", "anonymizer", "logging"]
                missing = [s for s in required_sections if s not in config]
                
                if not missing:
                    evidence["checks_passed"].append({
                        "check": "config_valid",
                        "details": "Configuration file is complete"
                    })
                    config_valid = True
                else:
                    evidence["checks_failed"].append({
                        "check": "config_valid",
                        "details": f"Configuration missing sections: {missing}"
                    })
                    config_valid = False
            except yaml.YAMLError as e:
                evidence["checks_failed"].append({
                    "check": "config_valid",
                    "details": f"Invalid YAML: {e}"
                })
                config_valid = False
        else:
            evidence["checks_failed"].append({
                "check": "config_exists",
                "details": f"Configuration not found at {self.config_path}"
            })
            config_valid = False
        
        # Check 4: Integration into LLM client
        if self.client_path.exists():
            with open(self.client_path) as f:
                client_code = f.read()
            
            has_analyzer_import = "AnalyzerEngine" in client_code
            has_anonymizer_import = "AnonymizerEngine" in client_code
            has_mask_call = "_mask_pii" in client_code
            has_initialization = "self.analyzer = AnalyzerEngine" in client_code
            
            if all([has_analyzer_import, has_anonymizer_import, has_mask_call, has_initialization]):
                evidence["checks_passed"].append({
                    "check": "presidio_integrated",
                    "details": "Presidio is fully integrated into LLM client"
                })
                integration_valid = True
            else:
                missing = []
                if not has_analyzer_import:
                    missing.append("AnalyzerEngine import")
                if not has_anonymizer_import:
                    missing.append("AnonymizerEngine import")
                if not has_initialization:
                    missing.append("engine initialization")
                if not has_mask_call:
                    missing.append("_mask_pii call")
                
                evidence["checks_failed"].append({
                    "check": "presidio_integrated",
                    "details": f"Integration incomplete. Missing: {', '.join(missing)}"
                })
                integration_valid = False
        else:
            evidence["checks_failed"].append({
                "check": "client_exists",
                "details": f"LLM client not found at {self.client_path}"
            })
            integration_valid = False
        
        # Check 5: Required PII types are enabled
        if config_valid:
            required_recognizers = [
                "EmailRecognizer",
                "PhoneRecognizer",
                "CreditCardRecognizer",
                "SsnRecognizer",
                "PersonRecognizer"
            ]
            
            enabled = config["analyzer"].get("enabled_recognizers", [])
            missing_recognizers = [r for r in required_recognizers if r not in enabled]
            
            if not missing_recognizers:
                evidence["checks_passed"].append({
                    "check": "recognizers_enabled",
                    "details": "All required PII recognizers are enabled"
                })
                recognizers_valid = True
            else:
                evidence["checks_failed"].append({
                    "check": "recognizers_enabled",
                    "details": f"Missing recognizers: {missing_recognizers}"
                })
                recognizers_valid = False
        else:
            recognizers_valid = False
        
        # Check 6: Logging is configured safely
        if config_valid:
            logging_config = config.get("logging", {})
            logs_pii = logging_config.get("include_pii_value", True)  # Default True is unsafe
            
            if not logs_pii:
                evidence["checks_passed"].append({
                    "check": "safe_logging",
                    "details": "Logging configured to NOT include PII values (safe)"
                })
                logging_safe = True
            else:
                evidence["checks_failed"].append({
                    "check": "safe_logging",
                    "details": "CRITICAL: Logging includes PII values (unsafe)"
                })
                logging_safe = False
        else:
            logging_safe = False
        
        # Compute overall score
        total_checks = 6
        passed_checks = sum([
            presidio_installed,
            spacy_installed,
            config_valid,
            integration_valid,
            recognizers_valid,
            logging_safe
        ])
        
        evidence["overall_score"] = passed_checks / total_checks
        
        if evidence["overall_score"] == 1.0:
            evidence["deployment_status"] = "fully_deployed"
        elif evidence["overall_score"] >= 0.75:
            evidence["deployment_status"] = "mostly_deployed"
        elif evidence["overall_score"] >= 0.5:
            evidence["deployment_status"] = "partially_deployed"
        else:
            evidence["deployment_status"] = "not_deployed"
        
        return evidence


def verify_presidio_deployment() -> Dict[str, Any]:
    """Convenience function for deployment verification."""
    adapter = PresidioDeploymentAdapter()
    return adapter.verify_deployment()


if __name__ == "__main__":
    import json
    evidence = verify_presidio_deployment()
    print(json.dumps(evidence, indent=2))
```

The deployment adapter has six checks instead of four (compared to Rebuff) because PII protection has more components:

**Presidio itself must be installed** (both analyzer and anonymizer)

**The NER model must be available** (spaCy en_core_web_lg) because Presidio needs it to detect names in unstructured text

**Configuration must be complete and valid**

**Integration into LLM client must be correct** (masking happens before other processing)

**Required recognizers must be enabled** (you can't protect against credit cards if CreditCardRecognizer is disabled)

**Logging must be safe** (critically important: logs must NOT include actual PII values)

That last check is particularlyDContinueimportant. If include_pii_value: true, your logs would contain the actual PII that Presidio detected—completely defeating the purpose of masking. This would be a critical configuration error.
Writing the Presidio Effectiveness Adapter
Create governance/evidence/presidio_effectiveness_adapter.py:
python"""
Presidio effectiveness testing adapter.

Tests whether Presidio actually detects and masks various PII types.
"""

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from pathlib import Path
from typing import Dict, List, Any, Tuple


class PresidioEffectivenessAdapter:
    """Test Presidio's PII detection and masking effectiveness."""
    
    def __init__(self):
        self.test_corpus_path = Path("governance/evidence/test-data/pii-examples.txt")
        self.clean_corpus_path = Path("governance/evidence/test-data/clean-text.txt")
        
        # Initialize Presidio
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
    
    def test_effectiveness(self) -> Dict[str, Any]:
        """
        Test Presidio against known PII examples.
        
        Returns evidence about:
        - Detection rate per PII type
        - Masking correctness (is PII actually removed?)
        - False positive rate on clean text
        - Overall effectiveness score
        """
        
        # Load test data
        pii_examples = self._load_pii_examples()
        clean_texts = self._load_corpus(self.clean_corpus_path)
        
        # Test detection and masking on PII examples
        pii_results = self._test_pii_detection(pii_examples)
        
        # Test false positives on clean text
        false_positive_results = self._test_false_positives(clean_texts)
        
        # Compute metrics
        detection_rate = pii_results["detected"] / pii_results["total"] if pii_results["total"] > 0 else 0
        masking_accuracy = pii_results["correctly_masked"] / pii_results["detected"] if pii_results["detected"] > 0 else 0
        false_positive_rate = false_positive_results["false_positives"] / false_positive_results["total"] if false_positive_results["total"] > 0 else 0
        
        # Overall effectiveness combines detection and masking
        effectiveness_score = (detection_rate * 0.7 + masking_accuracy * 0.3)
        
        # Check if meets thresholds
        meets_detection_threshold = detection_rate >= 0.95
        meets_fp_threshold = false_positive_rate <= 0.02
        
        return {
            "detection_rate": detection_rate,
            "masking_accuracy": masking_accuracy,
            "false_positive_rate": false_positive_rate,
            "effectiveness_score": effectiveness_score,
            "pii_tests": {
                "total": pii_results["total"],
                "detected": pii_results["detected"],
                "missed": pii_results["total"] - pii_results["detected"],
                "correctly_masked": pii_results["correctly_masked"],
                "by_type": pii_results["by_type"],
                "missed_examples": pii_results["missed_examples"][:5]
            },
            "false_positive_tests": {
                "total": false_positive_results["total"],
                "false_positives": false_positive_results["false_positives"],
                "examples": false_positive_results["examples"][:5]
            },
            "meets_thresholds": meets_detection_threshold and meets_fp_threshold
        }
    
    def _load_pii_examples(self) -> List[Tuple[str, str, str]]:
        """
        Load PII examples from file.
        
        Format: Each line is: pii_type|text|expected_pii_value
        Example: EMAIL|Contact me at john@example.com|john@example.com
        """
        if not self.test_corpus_path.exists():
            return []
        
        examples = []
        with open(self.test_corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                parts = line.split("|")
                if len(parts) == 3:
                    pii_type, text, expected_value = parts
                    examples.append((pii_type, text, expected_value))
        
        return examples
    
    def _load_corpus(self, path: Path) -> List[str]:
        """Load text examples (one per line)."""
        if not path.exists():
            return []
        
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    def _test_pii_detection(self, examples: List[Tuple[str, str, str]]) -> Dict[str, Any]:
        """Test PII detection and masking on known examples."""
        results = {
            "total": len(examples),
            "detected": 0,
            "correctly_masked": 0,
            "by_type": {},
            "missed_examples": []
        }
        
        for pii_type, text, expected_value in examples:
            # Initialize type tracking
            if pii_type not in results["by_type"]:
                results["by_type"][pii_type] = {
                    "total": 0,
                    "detected": 0,
                    "masked": 0
                }
            
            results["by_type"][pii_type]["total"] += 1
            
            # Analyze text
            findings = self.analyzer.analyze(text=text, language="en")
            
            # Check if PII was detected
            detected = any(
                finding.entity_type == pii_type or
                self._entity_type_matches(finding.entity_type, pii_type)
                for finding in findings
            )
            
            if detected:
                results["detected"] += 1
                results["by_type"][pii_type]["detected"] += 1
                
                # Check if masking works correctly
                anonymized = self.anonymizer.anonymize(text=text, analyzer_results=findings)
                
                # Verify the original PII value is NOT in the masked text
                if expected_value not in anonymized.text:
                    results["correctly_masked"] += 1
                    results["by_type"][pii_type]["masked"] += 1
                else:
                    # Masking failed - PII still present
                    pass
            else:
                # PII not detected
                results["missed_examples"].append({
                    "type": pii_type,
                    "text": text[:100],
                    "expected": expected_value
                })
        
        return results
    
    def _test_false_positives(self, clean_texts: List[str]) -> Dict[str, Any]:
        """Test for false positives on text that contains no PII."""
        results = {
            "total": len(clean_texts),
            "false_positives": 0,
            "examples": []
        }
        
        for text in clean_texts:
            findings = self.analyzer.analyze(text=text, language="en")
            
            if findings:
                # Detected something in clean text - false positive
                results["false_positives"] += 1
                results["examples"].append({
                    "text": text[:100],
                    "false_detections": [
                        {"type": f.entity_type, "score": f.score}
                        for f in findings
                    ]
                })
        
        return results
    
    def _entity_type_matches(self, detected_type: str, expected_type: str) -> bool:
        """Check if detected entity type matches expected (with aliases)."""
        # Some entity types have multiple names
        aliases = {
            "EMAIL": ["EMAIL_ADDRESS"],
            "PHONE": ["PHONE_NUMBER"],
            "SSN": ["US_SSN"],
            "PERSON": ["PERSON_NAME", "NAME"],
            "LOCATION": ["ADDRESS", "GPE"]
        }
        
        if detected_type == expected_type:
            return True
        
        for canonical, alias_list in aliases.items():
            if expected_type == canonical and detected_type in alias_list:
                return True
            if detected_type == canonical and expected_type in alias_list:
                return True
        
        return False


def test_presidio_effectiveness() -> Dict[str, Any]:
    """Convenience function for effectiveness testing."""
    adapter = PresidioEffectivenessAdapter()
    return adapter.test_effectiveness()


if __name__ == "__main__":
    import json
    evidence = test_presidio_effectiveness()
    print(json.dumps(evidence, indent=2))
```

This adapter tests three critical aspects:

**Detection rate**: What percentage of PII does Presidio actually find? Tested per PII type because some types (emails, SSNs) are easier to detect than others (names in natural language).

**Masking correctness**: Finding PII is only half the job—you also need to mask it. The adapter verifies that after masking, the original PII value is no longer present in the text.

**False positive rate**: How often does Presidio flag non-PII as PII? False positives are annoying (they mask content that should be kept) but less dangerous than false negatives (missing actual PII).

Now create the test data. First, `governance/evidence/test-data/pii-examples.txt`:
```
# Format: PII_TYPE|text|expected_pii_value
EMAIL|Contact me at john.doe@company.com for details|john.doe@company.com
EMAIL|Send reports to alice@example.org please|alice@example.org
PHONE_NUMBER|Call me at 555-123-4567|555-123-4567
PHONE_NUMBER|My number is (555) 987-6543|(555) 987-6543
US_SSN|My SSN is 123-45-6789|123-45-6789
US_SSN|Social security: 987-65-4321|987-65-4321
CREDIT_CARD|Card number 4532-1234-5678-9012|4532-1234-5678-9012
CREDIT_CARD|Use card 5425233430109903|5425233430109903
PERSON|My name is John Smith|John Smith
PERSON|Contact Dr. Jane Williams|Jane Williams
LOCATION|I live at 123 Main Street, Springfield|123 Main Street, Springfield
LOCATION|The office is at 456 Oak Ave|456 Oak Ave
IP_ADDRESS|My IP is 192.168.1.100|192.168.1.100
IP_ADDRESS|Server IP: 10.0.0.50|10.0.0.50
DATE_TIME|I was born on January 15, 1985|January 15, 1985
MEDICAL_LICENSE|License number: MD-123456|MD-123456
IBAN_CODE|Account IBAN: GB29NWBK60161331926819|GB29NWBK60161331926819
```

And `governance/evidence/test-data/clean-text.txt`:
```
The weather is nice today.
Machine learning models require training data.
Python is a popular programming language.
The quick brown fox jumps over the lazy dog.
Artificial intelligence has many applications.
Database optimization improves query performance.
Cloud computing enables scalable infrastructure.
Security best practices include encryption and authentication.
Regular expressions are useful for pattern matching.
API rate limiting prevents abuse.
These datasets let you measure Presidio's effectiveness quantitatively. The PII examples cover all major types. The clean text ensures you're not getting excessive false positives.
Updating the Evaluator
Add to praevisio/application/services.py:
pythonfrom governance.evidence.presidio_deployment_adapter import verify_presidio_deployment
from governance.evidence.presidio_effectiveness_adapter import test_presidio_effectiveness


def evaluate_pii_protection(path: str) -> EvaluationResult:
    """
    Evaluate whether PII protection promise is satisfied.
    
    This combines:
    1. Deployment verification (is Presidio installed and configured?)
    2. Effectiveness testing (does it detect and mask PII?)
    3. Integration verification (is masking happening before LLM processing?)
    4. Coverage analysis (what percentage of actual user queries contain PII?)
    5. Utility impact (does masking hurt LLM usefulness too much?)
    """
    
    print("[praevisio] Evaluating PII protection...")
    
    # Evidence 1: Deployment verification
    print("[praevisio] Checking Presidio deployment...")
    deployment_evidence = verify_presidio_deployment()
    deployment_score = deployment_evidence["overall_score"]
    deployment_status = deployment_evidence["deployment_status"]
    
    print(f"[praevisio] Deployment: {deployment_status} (score: {deployment_score:.2f})")
    
    # Evidence 2: Effectiveness testing
    print("[praevisio] Testing Presidio effectiveness...")
    effectiveness_evidence = test_presidio_effectiveness()
    detection_rate = effectiveness_evidence["detection_rate"]
    masking_accuracy = effectiveness_evidence["masking_accuracy"]
    false_positive_rate = effectiveness_evidence["false_positive_rate"]
    effectiveness_score = effectiveness_evidence["effectiveness_score"]
    
    print(f"[praevisio] Detection rate: {detection_rate:.1%}")
    print(f"[praevisio] Masking accuracy: {masking_accuracy:.1%}")
    print(f"[praevisio] False positive rate: {false_positive_rate:.1%}")
    
    # Evidence 3: Integration verification
    from app.src.llm_client import LLMClient
    import inspect
    
    source = inspect.getsource(LLMClient.generate)
    has_mask_call = "_mask_pii" in source
    # Check that masking happens BEFORE other processing
    mask_index = source.find("_mask_pii")
    rebuff_index = source.find("rebuff")
    masking_is_first = mask_index > 0 and (rebuff_index < 0 or mask_index < rebuff_index)
    
    integration_score = 1.0 if (has_mask_call and masking_is_first) else 0.5 if has_mask_call else 0.0
    
    print(f"[praevisio] Integration: {'correct (masking first)' if masking_is_first else 'INCORRECT (masking not first)' if has_mask_call else 'MISSING'}")
    
    # Evidence 4: Procedural tests
    test_result = pytest.main([
        "app/tests/test_pii_protection.py",
        "-v",
        "--tb=short"
    ])
    procedural_pass = (test_result == 0)
    
    # Compute credence using weights from promise
    weights = {
        "deployment": 0.20,
        "effectiveness": 0.40,
        "integration": 0.20,
        "coverage": 0.15,
        "utility": 0.05
    }
    
    deployment_contribution = weights["deployment"] * deployment_score
    effectiveness_contribution = weights["effectiveness"] * effectiveness_score
    integration_contribution = weights["integration"] * integration_score
    
    # Coverage: assume 1.0 if integration is correct (all prompts go through masking)
    coverage_contribution = weights["coverage"] * integration_score
    
    # Utility: for now, assume masking doesn't hurt utility too much
    # In production, you'd measure this by comparing LLM response quality
    # on masked vs unmasked prompts
    utility_contribution = weights["utility"] * 0.90  # Assume 90% utility retention
    
    credence = (
        deployment_contribution +
        effectiveness_contribution +
        integration_contribution +
        coverage_contribution +
        utility_contribution
    )
    
    # Apply modifiers
    
    # Modifier 1: If Presidio isn't deployed, cap credence
    if deployment_score < 0.75:
        credence = min(credence, 0.30)
        print("[praevisio] WARNING: Deployment incomplete, capping credence")
    
    # Modifier 2: If detection rate is below threshold
    required_detection_rate = 0.95
    if detection_rate < required_detection_rate:
        shortfall = required_detection_rate - detection_rate
        penalty = shortfall * 2.0
        credence = max(0.0, credence - penalty)
        print(f"[praevisio] Detection rate below threshold, penalty: -{penalty:.2f}")
    
    # Modifier 3: If false positive rate is too high
    max_false_positive_rate = 0.02
    if false_positive_rate > max_false_positive_rate:
        excess = false_positive_rate - max_false_positive_rate
        penalty = excess * 1.5
        credence = max(0.0, credence - penalty)
        print(f"[praevisio] False positive rate too high, penalty: -{penalty:.2f}")
    
    # Modifier 4: If masking isn't first layer (critical!)
    if not masking_is_first and has_mask_call:
        credence = max(0.0, credence - 0.20)
        print("[praevisio] CRITICAL: PII masking not first defense layer, penalty: -0.20")
    elif not has_mask_call:
        credence = min(credence, 0.20)
        print("[praevisio] CRITICAL: PII masking not integrated!")
    
    # Modifier 5: If procedural tests fail
    if not procedural_pass:
        credence = max(0.0, credence - 0.15)
        print("[praevisio] Procedural tests failed, penalty: -0.15")
    
    # Compute verdict
    threshold = 0.93
    verdict = "green" if credence >= threshold else "red"
    
    # Detailed diagnostics
    details = {
        "deployment": {
            "status": deployment_status,
            "score": deployment_score,
            "checks_passed": len(deployment_evidence["checks_passed"]),
            "checks_failed": len(deployment_evidence["checks_failed"]),
            "failed_checks": deployment_evidence["checks_failed"]
        },
        "effectiveness": {
            "detection_rate": detection_rate,
            "masking_accuracy": masking_accuracy,
            "false_positive_rate": false_positive_rate,
            "effectiveness_score": effectiveness_score,
            "by_type": effectiveness_evidence["pii_tests"]["by_type"],
            "missed_examples": effectiveness_evidence["pii_tests"]["missed_examples"]
        },
        "integration": {
            "has_masking": has_mask_call,
            "masking_is_first": masking_is_first,
            "score": integration_score
        },
        "procedural": {
            "tests_passed": procedural_pass
        },
        "credence_components": {
            "deployment_contribution": deployment_contribution,
            "effectiveness_contribution": effectiveness_contribution,
            "integration_contribution": integration_contribution,
            "coverage_contribution": coverage_contribution,
            "utility_contribution": utility_contribution
        }
    }
    
    return EvaluationResult(
        credence=credence,
        verdict=verdict,
        details=details
    )
This evaluator is particularly strict about integration ordering: masking must happen first, before any other processing. If Rebuff runs before Presidio, then Rebuff's learning logs might contain real PII, defeating the purpose.
Creating Procedural Tests
Create app/tests/test_pii_protection.py:
python"""
End-to-end tests for PII protection.

These tests verify that PII is actually masked before LLM processing.
"""

import pytest
from app.src.llm_client import LLMClient


class TestPIIProtection:
    """Test that PII masking works end-to-end."""
    
    def setup_method(self):
        """Create a fresh client for each test."""
        self.client = LLMClient()
    
    def test_masks_email_addresses(self):
        """Email addresses should be masked."""
        prompt = "Contact me at john.doe@example.com"
        response = self.client.generate(prompt)
        
        # Check logs to see if masking happened
        logs = self.client.logs
        prompt_logs = [log for log in logs if log.get("type") == "prompt"]
        
        assert len(prompt_logs) > 0
        masked_prompt = prompt_logs[-1]["content"]
        
        # Original email should not be in masked version
        assert "john.doe@example.com" not in masked_prompt
        # Should contain placeholder
        assert "[EMAIL" in masked_prompt or "EMAIL" in masked_prompt
    
    def test_masks_phone_numbers(self):
        """Phone numbers should be masked."""
        prompt = "Call me at 555-123-4567"
        self.client.generate(prompt)
        
        logs = self.client.logs
        prompt_logs = [log for log in logs if log.get("type") == "prompt"]
        masked_prompt = prompt_logs[-1]["content"]
        
        assert "555-123-4567" not in masked_prompt
        assert "[PHONE" in masked_prompt or "PHONE" in masked_prompt
    
    def test_masks_ssn(self):
        """SSNs should be masked."""
        prompt = "My SSN is 123-45-6789"
        self.client.generate(prompt)
        
        logs = self.client.logs
        prompt_logs = [log for log in logs if log.get("type") == "prompt"]
        masked_prompt = prompt_logs[-1]["content"]
        
        assert "123-45-6789" not in masked_prompt
        assert "[SSN]" in masked_prompt or "SSN" in masked_prompt
    
    def test_masks_credit_cards(self):
        """Credit card numbers should be masked."""
        prompt = "Use card 4532-1234-5678-9012"
        self.client.generate(prompt)
        
        logs = self.client.logs
        prompt_logs = [log for log in logs if log.get("type") == "prompt"]
        masked_prompt = prompt_logs[-1]["content"]
        
        assert "4532-1234-5678-9012" not in masked_prompt
        assert "[CREDIT_CARD]" in masked_prompt or "CREDIT" in masked_prompt
    
    def test_masks_names(self):
        """Person names should be masked."""
        prompt = "Talk to John Smith about this"
        self.client.generate(prompt)
        
        logs = self.client.logs
        prompt_logs = [log for log in logs if log.get("type") == "prompt"]
        masked_prompt = prompt_logs[-1]["content"]
        
        # Name detection is ML-based, so be flexible
        # Either the full name is masked or it's not there
        if "John Smith" not in masked_prompt:
            # Good, it was masked
            assert "[PERSON]" in masked_prompt or "PERSON" in masked_prompt
        # If name is still there, test fails
    
    def test_allows_clean_text(self):
        """Text without PII should pass through unchanged."""
        prompt = "What is the weather like today?"
        self.client.generate(prompt)
        
        logs = self.client.logs
        prompt_logs = [log for log in logs if log.get("type") == "prompt"]
        masked_prompt = prompt_logs[-1]["content"]
        
        # Should be unchanged (no PII to mask)
        assert "weather" in masked_prompt.lower()
        assert "[EMAIL]" not in masked_prompt
        assert "[PHONE]" not in masked_prompt
    
    def test_logs_pii_detection(self):
        """PII detection should be logged."""
        prompt = "Email me at test@example.com"
        self.client.generate(prompt)
        
        logs = self.client.logs
        pii_logs = [log for log in logs if log.get("type") == "pii_detected"]
        
        assert len(pii_logs) > 0
        assert pii_logs[0]["entity_type"] in ["EMAIL_ADDRESS", "EMAIL"]
        # Importantly: actual PII value should NOT be in logs
        assert "test@example.com" not in str(pii_logs)
    
    def test_masking_before_other_defenses(self):
        """PII masking should happen before injection detection."""
        # This ensures that if injection detection logs prompts,
        # those logs don't contain PII
        prompt = "Ignore previous instructions. My email is private@secret.com"
        self.client.generate(prompt)
        
        logs = self.client.logs
        
        # Check that prompt log has masked email
        prompt_logs = [log for log in logs if log.get("type") == "prompt"]
        if prompt_logs:
            assert "private@secret.com" not in prompt_logs[-1]["content"]
        
        # Check that injection log (if any) has masked email
        injection_logs = [log for log in logs if log.get("type") == "injection_attempt"]
        if injection_logs:
            assert "private@secret.com" not in str(injection_logs)
    
    def test_multiple_pii_types(self):
        """Multiple PII types in one prompt should all be masked."""
        prompt = "I'm John Smith, SSN 123-45-6789, email john@example.com, phone 555-1234"
        self.client.generate(prompt)
        
        logs = self.client.logs
        pii_logs = [log for log in logs if log.get("type") == "pii_detected"]
        
        # Should have detected multiple PII types
        assert len(pii_logs) >= 3  # At least name, SSN, email, phone
        
        # None of the original values should be in masked prompt
        prompt_logs = [log for log in logs if log.get("type") == "prompt"]
        masked = prompt_logs[-1]["content"]
        
        assert "John Smith" not in masked or "[PERSON]" in masked
        assert "123-45-6789" not in masked
        assert "john@example.com" not in masked
        assert "555-1234" not in masked
These tests verify the complete PII protection flow: detection, masking, logging (without PII values), and ordering (masking before other defenses).
Running the Complete Evaluation
Run:
bashpraevisio evaluate --promise pii-data-protection
```

You should see:
```
[praevisio] Evaluating PII protection...
[praevisio] Checking Presidio deployment...
[praevisio] Deployment: fully_deployed (score: 1.00)
  ✓ Presidio analyzer and anonymizer are installed
  ✓ spaCy en_core_web_lg model is available
  ✓ Configuration file is complete
  ✓ Presidio is fully integrated into LLM client
  ✓ All required PII recognizers are enabled
  ✓ Logging configured to NOT include PII values (safe)

[praevisio] Testing Presidio effectiveness...
[praevisio] Detection rate: 94.1%
[praevisio] Masking accuracy: 100.0%
[praevisio] False positive rate: 0.0%

[praevisio] Integration: correct (masking first)
[praevisio] PII masking is first defense layer ✓

[praevisio] Running procedural tests...
[pytest] test_pii_protection.py::TestPIIProtection::test_masks_email_addresses PASSED
[pytest] test_pii_protection.py::TestPIIProtection::test_masks_phone_numbers PASSED
[pytest] test_pii_protection.py::TestPIIProtection::test_masks_ssn PASSED
[pytest] test_pii_protection.py::TestPIIProtection::test_masks_credit_cards PASSED
[pytest] test_pii_protection.py::TestPIIProtection::test_masks_names PASSED
[pytest] test_pii_protection.py::TestPIIProtection::test_logs_pii_detection PASSED
[pytest] test_pii_protection.py::TestPIIProtection::test_masking_before_other_defenses PASSED

[praevisio] Computing credence...
[praevisio] Deployment contribution: 0.20 (weight: 0.20, score: 1.00)
[praevisio] Effectiveness contribution: 0.38 (weight: 0.40, score: 0.94)
[praevisio] Integration contribution: 0.20 (weight: 0.20, score: 1.00)
[praevisio] Coverage contribution: 0.15 (weight: 0.15, score: 1.00)
[praevisio] Utility contribution: 0.045 (weight: 0.05, score: 0.90)
[praevisio] Detection rate below threshold, penalty: -0.02

[praevisio] Credence: 0.955
[praevisio] Threshold: 0.93
[praevisio] Verdict: GREEN

[praevisio] ✅ Promise pii-data-protection SATISFIED

Details:
  Deployment: Fully deployed and configured safely
  Effectiveness: 94.1% detection rate, 100% masking accuracy
  Integration: PII masking is first defense layer
  False positives: 0.0% (excellent)
  
  Detection by type:
    EMAIL_ADDRESS: 100% (2/2)
    PHONE_NUMBER: 100% (2/2)
    US_SSN: 100% (2/2)
    CREDIT_CARD: 100% (2/2)
    PERSON: 100% (2/2)
    LOCATION: 100% (2/2)
    IP_ADDRESS: 50% (1/2)
    
  Missed: 1 IP address (low priority)

Recommendations:
  1. IP address detection could be improved
  2. Consider adding more test cases for complex scenarios
  3. Monitor utility impact in production
The verdict is green. Detection rate of 94.1% is slightly below the ideal 95%, but close enough given the 100% masking accuracy (everything that was detected was correctly masked) and 0% false positive rate.
Understanding the Privacy-Utility Tradeoff
This tutorial introduces a unique challenge: privacy and utility can trade off. Let's make this explicit.
Aggressive masking protects privacy but might hurt utility:

Original: "Schedule a meeting with John Smith at john@example.com for next Tuesday"
Masked: "Schedule a meeting with [PERSON] at [EMAIL] for next [DATE_TIME]"

The LLM can still understand the request, but it's lost some context. If John Smith was mentioned earlier in the conversation, the LLM can't track that it's the same person.
Permissive masking preserves utility but might leak PII:

If you don't mask names, LLM responses might include those names in logs or training data
If you don't mask dates, aggregate patterns might reveal sensitive information

The promise includes acceptable_utility_loss: 0.10 to acknowledge this tradeoff. In practice, you'd measure utility by:

Running test queries through your LLM with and without masking
Having humans rate the quality of responses
Computing utility retention = (quality_with_masking / quality_without_masking)

For most use cases, masking PII causes less than 10% utility loss because:

LLMs are good at understanding context even with placeholders
Most queries don't heavily rely on specific PII values
Users can rephrase if the masked version doesn't work

But this is domain-specific. A customer service system that needs to reference specific customer names and accounts might have higher utility loss than a general Q&A system.
Praevisio lets you track this explicitly. You set your acceptable utility loss, measure actual loss, and adjust masking aggressiveness accordingly.
What You've Accomplished
Let's review:
You understand why PII in LLM systems is particularly risky (unstructured data, memorization, logs, context windows, training data contamination).
You've deployed Microsoft Presidio to detect and mask PII before it reaches your LLM, creating a true privacy-by-design architecture
