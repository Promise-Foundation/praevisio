# Tutorial 1 – Hello World: Logging & Credence (ABDUCTIO)

## What You'll Learn

This tutorial shows the current, supported workflow:

- configure governance locally in your repo (`.praevisio.yaml`)
- add a simple LLM boundary with logging
- run `praevisio evaluate-commit` to produce credence + audit artifacts
- inspect a replayable audit trace

**Important:** You never edit Praevisio or abductio-core source. All customization lives in your repo.

**Where to run this:** These steps are meant to run in the repository you are governing (an “app repo” with `app/`, `tests/`, `governance/`). If you are reading this inside the Praevisio source repo, run it inside `tmp-eval-repo/`.

## Tiers (Who This Is For)

- **Tier 1 (developer):** see a clear pass/fail and a fixable line.
- **Tier 2 (configurer):** tune thresholds, add tests, and add collectors.
- **Tier 3 (power user):** inspect audit traces and evidence artifacts.

This tutorial is Tier 1 + a small Tier 2 slice.

## Step 1: Create a Minimal Boundary + Test

Use a wrapper boundary instead of scattered calls. This pattern scales to real systems.

`app/src/llm_gateway.py`:
```python
from __future__ import annotations
from pathlib import Path


def log(prompt: str, log_path: Path) -> None:
    with log_path.open("a", encoding="utf-8") as f:
        f.write(prompt + "\n")


def call_llm(prompt: str) -> str:
    return f"echo:{prompt}"


def generate(prompt: str, log_path: Path) -> str:
    log(prompt, log_path)
    return call_llm(prompt)
```

`tests/test_logging.py`:
```python
from __future__ import annotations

from app.src.llm_gateway import generate


def test_generate_logs_and_calls(tmp_path) -> None:
    log_path = tmp_path / "llm_log.txt"
    assert generate("hello", log_path) == "echo:hello"
    assert generate("world", log_path) == "echo:world"
    assert log_path.read_text(encoding="utf-8") == "hello\nworld\n"
```

## Step 2: Add a Local Governance Config

Create `.praevisio.yaml` in your repo:
```yaml
evaluation:
  promise_id: llm-input-logging
  threshold: 0.95
  severity: high
  pytest_targets:
    - tests/test_logging.py
  semgrep_rules_path: governance/evidence/semgrep_rules.yaml
  semgrep_callsite_rule_id: llm-call-site
  semgrep_violation_rule_id: llm-call-must-log
  run_dir: .praevisio/runs
hooks: []
```

This tells Praevisio **where evidence comes from**. ABDUCTIO consumes that evidence and computes credence.
Severity and thresholds belong in `.praevisio.yaml` (not in promise files).
If you need to tune pytest verbosity, set `pytest_args` (defaults to `["-q", "--disable-warnings"]`).
Praevisio resolves `promise_id` by loading `governance/promises/{promise_id}.yaml` in your repo. The `docs/governance/` tree is documentation only.

## Step 3: Add the Promise File

Create `governance/promises/llm-input-logging.yaml`:

```yaml
id: llm-input-logging
version: 0.1.0
domain: /llm/logging
statement: All LLM input prompts must be logged at the boundary.
critical: true
success_criteria:
  credence_threshold: 0.95
  evidence_types:
    - direct_observational
    - procedural
parameters: {}
```

## Step 4: Add a Semgrep Rule (Direct Observational Evidence)

Create `governance/evidence/semgrep_rules.yaml`:
```yaml
rules:
  - id: llm-call-site
    languages: [python]
    message: LLM call site detected
    severity: INFO
    patterns:
      - pattern: call_llm($PROMPT)

  - id: llm-call-must-log
    languages: [python]
    message: LLM call detected without prior logging
    severity: ERROR
    patterns:
      - pattern: call_llm($PROMPT)
      - pattern-not-inside: |
          log($PROMPT, $LOG_PATH)
          ...
          call_llm($PROMPT)
```

Semgrep output is **direct observational evidence** about code structure. It doesn’t run your code.
In real projects, point the rule at your actual boundary function (for example, `LLMGateway.generate()` or your SDK wrapper), not a placeholder like `call_llm()`.

## Step 5: Run Evaluation

```bash
praevisio evaluate-commit . --config .praevisio.yaml --json
```

You’ll see JSON output with:
- `credence` and `verdict`
- `audit_path` and `manifest_path`
- evidence summaries and references

Example (trimmed):
```json
{
  "credence": 0.8,
  "verdict": "green",
  "details": {
    "audit_path": ".praevisio/runs/20251220T131822Z/audit.json",
    "manifest_path": ".praevisio/runs/20251220T131822Z/manifest.json",
    "evidence_refs": {
      "pytest": ["pytest:sha256:..."],
      "semgrep": ["semgrep:sha256:..."]
    }
  }
}
```

## Step 6: Replay the Audit

```bash
praevisio replay-audit --latest
```

This reconstructs the ledger deterministically from the audit trace. You should see the same credence as the evaluation output.

## What Credence Means (ABDUCTIO)

Praevisio **does not** manually weight evidence. It gathers evidence and ABDUCTIO computes:

- **credence**: probability the promise holds given evidence
- **confidence (k_root)**: how stable that belief is

Praevisio reports confidence; verdict gating depends on configured policy.

## Skipped Tests Penalty

If `pytest_targets` is empty or all tests are skipped, Praevisio marks tests as skipped and the evaluator applies a penalty (`p=0.2`) for the availability slot. To avoid that penalty, include at least one test in `pytest_targets`.

## Simulate a Violation

Remove the log call in `generate`:
```python
# log(prompt, log_path)
return call_llm(prompt)
```

Run:
```bash
praevisio evaluate-commit . --config .praevisio.yaml --json
```

Semgrep should report a violation, the defeater slot drops, and the verdict becomes **red**.

## Summary

You now have a real, replayable governance check:

- **Tier 1:** clear pass/fail
- **Tier 2:** local config + evidence sources
- **Tier 3:** audit + replay

Next: Tutorial 2 tightens static analysis coverage and rule specificity.

## Appendix (Tier 3): Inference Tuning

Most teams should not touch ABDUCTIO parameters. If you do, keep them in `.praevisio.yaml` under `evaluation` and treat them as advanced settings:

```yaml
evaluation:
  abductio_credits: 4
  abductio_tau: 0.70
  abductio_epsilon: 0.05
  abductio_gamma: 0.20
  abductio_alpha: 0.40
  abductio_beta: 1.0
  abductio_weight_cap: 3.0
  abductio_lambda_voi: 0.1
  abductio_world_mode: open
  abductio_required_slots:
    - slot_key: feasibility
      role: NEC
    - slot_key: availability
      role: NEC
    - slot_key: fit_to_key_features
      role: NEC
    - slot_key: defeater_resistance
      role: NEC
```

If you are not sure what these do, leave them at defaults.
