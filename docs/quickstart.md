# Quickstart

This quickstart shows the fastest way to run Praevisio against the in‑repo fixture.

## Install

```bash
pip install praevisio
```

Verify:

```bash
praevisio version
```

## Run the fixture

```bash
praevisio ci-gate fixtures/hello-world \
  --severity high \
  --enforce \
  --output logs/ci-gate-report.json \
  --config fixtures/hello-world/.praevisio.yaml
```

This produces audit artifacts under `fixtures/hello-world/.praevisio/runs/`.

## Replay the audit

```bash
praevisio replay-audit --latest --runs-dir fixtures/hello-world/.praevisio/runs --json
```

## Next steps

- Read Tutorials 1–3 in `docs/tutorials/` for a guided walk‑through.
- Use `praevisio install --config-path .praevisio.yaml` to scaffold your own repo.
