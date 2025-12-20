# Tutorial 7 – Third-Party Risk and Manual Oversight (Current Release)

> Note: Praevisio currently consumes **pytest pass/fail** and **semgrep coverage** only. Use tests to enforce manual approvals and risk registry checks.

**Where to run this:** in your governed app repo. If you are in the Praevisio source repo, work inside `tmp-eval-repo/`.
These tutorials assume you focus `.praevisio.yaml` on one promise at a time.

## What You'll Learn

- Represent manual approvals in a repo-local registry
- Write tests that enforce sign-off rules
- Gate releases on those approvals with Praevisio

## Add a Risk Registry

Create `governance/risk-register.yaml`:

```yaml
entries:
  - id: vendor-llm-2025-01
    vendor: "Acme LLM"
    review_status: "approved"
    reviewed_by: "security-team"
    reviewed_at: "2025-01-12"
    expires_at: "2025-07-12"
```

## Add the Promise File

Create `governance/promises/third-party-risk-reviewed.yaml`:

```yaml
id: third-party-risk-reviewed
version: 0.1.0
domain: /risk/third-party
statement: Third-party vendors must have current security reviews before use.
critical: true
success_criteria:
  credence_threshold: 0.90
  evidence_types:
    - procedural
parameters: {}
stake:
  credits: 0
```

## Add Tests That Enforce Policy

Create `tests/test_risk_registry.py`:

```python
import yaml
from pathlib import Path
from datetime import datetime


def test_vendor_reviews_are_current():
    registry = Path("governance/risk-register.yaml")
    data = yaml.safe_load(registry.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    assert entries, "Risk register is empty"

    now = datetime.utcnow().date()
    for entry in entries:
        assert entry.get("review_status") == "approved"
        expires_at = datetime.fromisoformat(entry["expires_at"]).date()
        assert expires_at >= now, f"Review expired for {entry.get('vendor')}"
```

This test turns a manual process into an enforceable gate. If a review expires, the test fails and the gate blocks release until the registry is updated.

If you don't already use PyYAML, install it in your project:

```bash
python -m pip install pyyaml
```

For CI stability, add it to your dependencies (for example `requirements.txt` or `pyproject.toml`).

## Configure Praevisio

Create `.praevisio.yaml`:

```yaml
evaluation:
  promise_id: third-party-risk-reviewed
  threshold: 0.90
  pytest_targets:
    - tests/test_risk_registry.py
hooks: []
```

## Run the Gate

```bash
praevisio ci-gate --config .praevisio.yaml --severity high --fail-on-violation
```

If you use severity thresholds, configure `evaluation.severity` and `evaluation.thresholds` as shown in Tutorial 3.
If approvals are missing or expired, the gate fails. The audit artifacts show the exact evidence used in the decision.
The registry is the only mutable artifact; you never edit Praevisio or abductio-core.

## Next Steps

To scale this, generate the risk registry from your GRC system and commit it as an artifact. Praevisio stays generic; your policy lives in your repo.
