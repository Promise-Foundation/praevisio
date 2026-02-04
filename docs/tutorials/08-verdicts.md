# Tutorial 8 – Verdicts & Decision Artifacts

## What You'll Learn

- where `decision.json` is written and what it contains
- how `overall_verdict` is computed from per‑promise outcomes
- how CI notifications are derived (action/impact/likelihood/confidence)
- how to validate determinism using audit replay

**Reminder:** configuration lives in your repo. No Praevisio core edits.
**Where to run this:** in your governed app repo. If you are in the Praevisio source repo, work inside `tmp-eval-repo/`.

## Run this tutorial with praevisio-lab (recommended)

Any lab case will produce decision artifacts. The CI‑gate case is the most useful for notifications:

```
cd ~/projects/praevisio-lab
python -m praevisio_lab run-case ci_gate_logging   --registry cases/manifest.yaml   --mode ci-gate   --workspace .praevisio-lab/work   --bundles-dir .praevisio-lab/bundles   --json
```

Artifacts will be written under `.praevisio/runs/<run_id>/`.

## Step 1: Produce a decision artifact

Run an evaluation:

```bash
praevisio evaluate-commit . --config .praevisio.yaml --json
```

This writes:
- `.praevisio/runs/<run_id>/audit.json`
- `.praevisio/runs/<run_id>/manifest.json`
- `.praevisio/runs/<run_id>/decision.json`

Note: `evaluate-commit` exits non‑zero on `red` or `error`.

## Step 2: Inspect `decision.json`

Open the latest decision:

```bash
ls -t .praevisio/runs/*/decision.json | head -n 1
```

Key fields:

- `schema_version`, `run_id`, `timestamp_utc`
- `policy` (thresholds, severity, tau, enforcement mode)
- `overall_verdict`
- `promise_results` (per‑promise credence + verdict)
- `audit_sha256` and `manifest_sha256`

Minimal example (redacted):

```json
{
  "schema_version": "1.0",
  "run_id": "20260204T173200Z",
  "timestamp_utc": "2026-02-04T17:32:00+00:00",
  "policy": {
    "threshold": 0.8,
    "thresholds": {"low": 0.6, "medium": 0.8, "high": 0.95},
    "severity": null,
    "tau": 0.7,
    "enforcement": {"mode": "evaluate-commit", "fail_on_violation": true}
  },
  "overall_verdict": "green",
  "promise_results": [
    {"promise_id": "llm-input-logging", "threshold": 0.8, "credence": 0.8, "verdict": "green"}
  ],
  "audit_sha256": "…",
  "manifest_sha256": "…"
}
```

## Step 3: CI notifications (decision + gate output)

`praevisio ci-gate` always writes `decision.json` and includes a `notification` payload.
Use `--enforce` (alias: `--fail-on-violation`) if you want CI to fail on red/error:

```bash
praevisio ci-gate . --enforce --config .praevisio.yaml
```

Notification logic:

- `action`: `change_blocked` for `red|error`, else `change_allowed`
- `impact`: derived from severity (`low|medium|high|critical`, default `medium`)
- `likelihood`: derived from credence (`near_certain|likely|possible|unlikely`)
- `confidence`: derived from `k_root` (`high|medium|low`)

Example:

```json
"notification": {
  "action": "change_allowed",
  "impact": "medium",
  "likelihood": "likely",
  "confidence": "medium",
  "summary": "change allowed for llm-input-logging (green)."
}
```

## Step 4: Determinism check with audit replay

Replay the latest audit and compare credence to `decision.json`:

```bash
praevisio replay-audit --latest --json
```

The replayed ledger should match the credence values stored in `decision.json`.

## Summary

- Every run produces a canonical `decision.json` next to the audit + manifest.
- `overall_verdict` rolls up per‑promise results; CI can enforce on red/error.
- `notification` is designed for ticketing and change‑management workflows.
