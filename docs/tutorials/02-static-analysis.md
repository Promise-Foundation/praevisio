# Tutorial 2 – Static Analysis That Scales (Semgrep + ABDUCTIO)

## What You'll Learn

- move from a toy string check to real Semgrep rules
- produce **direct observational evidence** (AST‑level checks)
- let ABDUCTIO compute credence/confidence (no custom math)

**You never edit Praevisio core.** All configuration is in your repo.
**Where to run this:** use your governed app repo. If you are in the Praevisio source repo, work inside `tmp-eval-repo/`.


## Run this tutorial with praevisio-lab (recommended)

If you want a ready-made repo with the Semgrep rules already wired, use the lab case:

```
cd ~/projects/praevisio-lab
python -m praevisio_lab run-case static_analysis_logging   --registry cases/manifest.yaml   --mode baseline-b   --workspace .praevisio-lab/work   --bundles-dir .praevisio-lab/bundles   --json
```

Tip: baseline-b is Semgrep-only evidence. If you want Semgrep to run inside praevisio mode,
set `semgrep_rules_path`, `semgrep_callsite_rule_id`, and `semgrep_violation_rule_id` in the
case config and rerun in `--mode praevisio`.

## Step 1: Strengthen the Rule

We’ll reuse the Semgrep rules from Tutorial 1, but now we’ll interpret coverage/violations and scope the rule to your real boundary.

In your repo, update:

`governance/evidence/semgrep_rules.yaml`:
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

This gives you two numbers:
- total call sites
- violations

Praevisio treats that as evidence; ABDUCTIO handles credence math.

## Step 2: Ensure Config Points to the Rules

`.praevisio.yaml`:
```yaml
evaluation:
  semgrep_rules_path: governance/evidence/semgrep_rules.yaml
  semgrep_callsite_rule_id: llm-call-site
  semgrep_violation_rule_id: llm-call-must-log
```

## Step 3: Run and Inspect Evidence

```bash
praevisio evaluate-commit . --config .praevisio.yaml --json
```

In the output, check:
- `details.evidence.semgrep_coverage`
- `details.evidence.violations_found`
- `details.evidence_refs.semgrep`
- `details.audit_path` and `details.manifest_path`

This is the **evidence pipeline**: Semgrep outputs artifacts, Praevisio records them, ABDUCTIO evaluates them.

## Step 4: Add a Violation

Create a second path that bypasses logging:
```python
from pathlib import Path


def generate_unlogged(prompt: str, log_path: Path) -> str:
    return call_llm(prompt)
```

Re‑run:
```bash
praevisio evaluate-commit . --config .praevisio.yaml --json
```

The `llm-call-must-log` rule should fire, defeater evidence drops, and the verdict should be **red**.

## Step 5: Scope to Your Real Boundary

Toy rules like `call_llm($PROMPT)` won’t match real systems. Scope the pattern to your actual boundary:

**Option A: boundary wrapper**
```yaml
patterns:
  - pattern: $GATEWAY.generate($PROMPT, $LOG_PATH)
```

**Option B: SDK call at the boundary**
```yaml
patterns:
  - pattern: client.responses.create(...)
```

Pick whichever matches your architecture and keep the rule focused on the approved path.

## Why This Is Better

- **AST‑aware**: rule matches structure, not strings
- **Replayable**: audit + manifest let you prove the decision later
- **No hand‑crafted credence math**: ABDUCTIO handles inference

Next: Tutorial 3 shows how to make this gate CI merges.
