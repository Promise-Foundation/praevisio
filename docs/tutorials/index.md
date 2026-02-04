# Tutorials: Praevisio AI Governance Lab

## Praevisio Lab quickstart

If you want runnable, ready-made tutorials, use the praevisio-lab cases and commands:

| Tutorial | Lab case | Command |
| --- | --- | --- |
| 01 Logging basics | `hello_world_logging` | `python -m praevisio_lab run-case hello_world_logging --registry cases/manifest.yaml --mode praevisio --workspace .praevisio-lab/work --bundles-dir .praevisio-lab/bundles --json` |
| 02 Static analysis | `static_analysis_logging` | `python -m praevisio_lab run-case static_analysis_logging --registry cases/manifest.yaml --mode baseline-b --workspace .praevisio-lab/work --bundles-dir .praevisio-lab/bundles --json` |
| 03 CI gate | `ci_gate_logging` | `python -m praevisio_lab run-case ci_gate_logging --registry cases/manifest.yaml --mode ci-gate --workspace .praevisio-lab/work --bundles-dir .praevisio-lab/bundles --json` |
| 04 Red-teaming | `red_team_promptfoo` | `PROMPTFOO_OPTIONAL=1 python -m praevisio_lab run-case red_team_promptfoo --registry cases/manifest.yaml --mode praevisio --workspace .praevisio-lab/work --bundles-dir .praevisio-lab/bundles --json` |
| 05 Prompt injection | `prompt_injection` | `python -m praevisio_lab run-case prompt_injection --registry cases/manifest.yaml --mode praevisio --workspace .praevisio-lab/work --bundles-dir .praevisio-lab/bundles --json` |
| 06 Privacy protection | `privacy_redaction` | `python -m praevisio_lab run-case privacy_redaction --registry cases/manifest.yaml --mode praevisio --workspace .praevisio-lab/work --bundles-dir .praevisio-lab/bundles --json` |
| 07 Third-party risk | `third_party_risk` | `python -m praevisio_lab run-case third_party_risk --registry cases/manifest.yaml --mode praevisio --workspace .praevisio-lab/work --bundles-dir .praevisio-lab/bundles --json` |
| 08 Verdicts & decisions | `ci_gate_logging` | `python -m praevisio_lab run-case ci_gate_logging --registry cases/manifest.yaml --mode ci-gate --workspace .praevisio-lab/work --bundles-dir .praevisio-lab/bundles --json` |

Notes:
- Use `~/projects/praevisio-lab` as your working directory.
- The lab cases mirror the tutorial repos and produce audit bundles you can inspect.

These hands-on tutorials turn Praevisio into a learn-by-doing AI governance lab.

Structure
- Each lesson introduces a real standards hook (NIST AI RMF / EU AI Act / ISO 42001) and at least one new governance artifact (promise, evidence, or gate).
- Lessons build on each other but are self-contained experiments.

Standards spine
- NIST AI RMF (Govern, Map, Measure, Manage) as the narrative spine
- EU AI Act Articles 12/19 (logging & record-keeping), 16/26 (provider/deployer obligations)
- ISO/IEC 42001:2023 (AI management system: lifecycle risk, oversight, improvement)

```{toctree}
:maxdepth: 1
:titlesonly:

01-logging-basics
02-static-analysis
03-branch-policy
04-red-teaming
05-prompt-injection
06-privacy-protection
07-third-party-risk
08-verdicts
```
