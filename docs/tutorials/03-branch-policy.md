# Tutorial 3 – CI Gate & Branch Policy

## What You'll Learn

- enforce promises in CI with `praevisio ci-gate`
- use severity thresholds from `.praevisio.yaml`
- publish audit artifacts for review

**Reminder:** configuration lives in your repo. No Praevisio core edits.
**Where to run this:** in your governed app repo. If you are in the Praevisio source repo, work inside `tmp-eval-repo/`.

## Step 1: Add Severity Thresholds

In `.praevisio.yaml`:
```yaml
evaluation:
  threshold: 0.95
  severity: high
  thresholds:
    high: 0.95
    medium: 0.90
```

`praevisio ci-gate` will use `thresholds[severity]` if provided; otherwise it falls back to `evaluation.threshold`.
Severity is configured in `.praevisio.yaml`, not in promise files.

## Step 2: CI Workflow Example

`.github/workflows/praevisio-ci.yml`:
```yaml
name: Praevisio Gate
on: [pull_request]

jobs:
  praevisio:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install praevisio
      - run: |
          praevisio ci-gate \
            --severity high \
            --fail-on-violation \
            --output logs/ci-gate-report.json \
            --config .praevisio.yaml
      - uses: actions/upload-artifact@v4
        with:
          name: praevisio-run
          path: |
            logs/ci-gate-report.json
            .praevisio/runs/**
```

If you are running the Praevisio source repository in CI, use:
```bash
python -m pip install -e .
```

## Step 3: Understand the Report

`logs/ci-gate-report.json` includes:
- verdict, credence, threshold
- audit and manifest paths/hashes

This makes decisions reviewable: you can replay audits and inspect evidence artifacts.

## Step 4: Local Pre‑Commit Gate

```bash
praevisio install-hooks
```

This installs a local pre‑commit hook that runs `praevisio pre-commit` before a commit.
It writes a script to `.git/hooks/pre-commit`. Remove it by deleting that file.

## Summary

- CI uses `praevisio ci-gate` + severity thresholds
- Audit + manifest artifacts make decisions replayable
- Local pre‑commit prevents regressions before CI
