# Tutorial 6 – Privacy Protection (Current Release)

> Note: Praevisio currently consumes **pytest pass/fail** and **semgrep coverage** only. For privacy checks, write tests that verify redaction and policy behavior.

**Where to run this:** in your governed app repo. If you are in the Praevisio source repo, work inside `tmp-eval-repo/`.
These tutorials assume you focus `.praevisio.yaml` on one promise at a time.

## What You'll Learn

- Add tests that verify PII redaction
- Gate deployments on those tests
- Keep the policy in your repo, not in Praevisio

## Example Redaction Boundary

Create a single boundary that all prompts flow through (for example `app/src/llm_gateway.py`). That boundary should:

- redact PII
- attach a trace id
- log or store redacted prompts

## Add Privacy Tests

Create `tests/test_privacy_redaction.py`:

```python
from app.src.llm_gateway import redact


def test_redacts_email_addresses():
    redacted = redact("Contact me at john@example.com")
    assert "john@example.com" not in redacted
    assert "[REDACTED_EMAIL]" in redacted


def test_redacts_phone_numbers():
    redacted = redact("Call me at 555-123-4567")
    assert "555-123-4567" not in redacted
    assert "[REDACTED_PHONE]" in redacted
```

If your system uses a third-party redaction library, this test becomes your enforcement point.
If you don’t already have `redact()` in your boundary, add a minimal implementation or wrap your existing redaction middleware.

Minimal example:

```python
import re

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(\+?1[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}\b")


def redact(text: str) -> str:
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    return text
```

## Add the Promise File

Create `governance/promises/llm-privacy-redaction.yaml`:

```yaml
id: llm-privacy-redaction
version: 0.1.0
domain: /llm/privacy
statement: The system must redact sensitive data before sending prompts to the LLM.
critical: true
success_criteria:
  credence_threshold: 0.90
  evidence_types:
    - procedural
parameters: {}
stake:
  credits: 0
```

## Configure Praevisio

Create `.praevisio.yaml`:

```yaml
evaluation:
  promise_id: llm-privacy-redaction
  threshold: 0.90
  pytest_targets:
    - tests/test_privacy_redaction.py
hooks: []
```

## Run the Gate

```bash
praevisio evaluate-commit . --config .praevisio.yaml --json
```

If tests fail, the verdict will be red. Praevisio also writes audit and manifest artifacts under `.praevisio/runs/`.

## Next Steps

If you want coverage-style checks (for example, verify every call site uses the gateway), add semgrep rules and point `semgrep_rules_path` to your rules file.
