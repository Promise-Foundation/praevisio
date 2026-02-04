# Minimal Feature Examples

Each example below is **atomic**: start from an empty directory and follow the steps to demonstrate a single feature with the smallest possible setup.

Assumptions:
- The `praevisio` CLI is on your PATH (if you use `uv`, substitute `uv run praevisio`).
- Python 3.11+ is available.

---

## Example 1 — Replayable audit trail (minimum viable run)

**Goal:** Produce a run with `manifest.json` + `audit.json`, then replay it.

**Steps (from an empty repo):**

```bash
mkdir demo-replay && cd demo-replay

mkdir -p governance/promises tests
cat > governance/promises/llm-input-logging.yaml <<'YAML'
id: llm-input-logging
statement: "All LLM calls are logged"
success_criteria:
  credence_threshold: 0.1
YAML

cat > .praevisio.yaml <<'YAML'
evaluation:
  promise_id: llm-input-logging
  threshold: 0.1
  pytest_targets: ["tests/test_smoke.py"]
  semgrep_rules_path: ""
YAML

cat > tests/test_smoke.py <<'PY'
def test_smoke():
    assert True
PY

praevisio evaluate-commit . --config .praevisio.yaml --json
praevisio replay-audit --latest --json
```

**Expected:** `evaluate-commit` writes `.praevisio/runs/<run_id>/audit.json` and `manifest.json`, and replay returns a reconstructed ledger.

---

## Example 2 — Strict determinism detects toolchain drift

**Goal:** Show `--strict-determinism` fails when the toolchain in the manifest doesn’t match.

**Steps (from an empty repo):**

```bash
mkdir demo-drift && cd demo-drift

mkdir -p governance/promises tests
cat > governance/promises/llm-input-logging.yaml <<'YAML'
id: llm-input-logging
statement: "All LLM calls are logged"
YAML

cat > .praevisio.yaml <<'YAML'
evaluation:
  promise_id: llm-input-logging
  threshold: 0.1
  pytest_targets: ["tests/test_smoke.py"]
  semgrep_rules_path: ""
YAML

cat > tests/test_smoke.py <<'PY'
def test_smoke():
    assert True
PY

praevisio evaluate-commit . --config .praevisio.yaml --json

python - <<'PY'
import json, glob
manifest = sorted(glob.glob(".praevisio/runs/*/manifest.json"))[-1]
data = json.load(open(manifest))
data["metadata"]["python_version"] = "0.0.0"
data["metadata"]["tool_versions"] = {"pytest": "0.0.0"}
json.dump(data, open(manifest, "w"), indent=2, sort_keys=True)
PY

praevisio replay-audit --latest --strict-determinism
```

**Expected:** replay exits non‑zero and prints a toolchain mismatch warning.

---

## Example 3 — Tamper‑evident audit pack verification

**Goal:** Export an audit pack, verify it, then show verification fails after tampering.

**Steps (from an empty repo):**

```bash
mkdir demo-auditpack && cd demo-auditpack

mkdir -p governance/promises tests
cat > governance/promises/llm-input-logging.yaml <<'YAML'
id: llm-input-logging
statement: "All LLM calls are logged"
YAML

cat > .praevisio.yaml <<'YAML'
evaluation:
  promise_id: llm-input-logging
  threshold: 0.1
  pytest_targets: ["tests/test_smoke.py"]
  semgrep_rules_path: ""
YAML

cat > tests/test_smoke.py <<'PY'
def test_smoke():
    assert True
PY

praevisio evaluate-commit . --config .praevisio.yaml --json
run_id=$(ls .praevisio/runs | tail -n 1)
praevisio export --run "$run_id" --out auditpack.zip
praevisio verify auditpack.zip

python - <<'PY'
import zipfile, json
with zipfile.ZipFile("auditpack.zip") as z:
    manifest = json.loads(z.read("manifest.json"))
manifest["metadata"]["tampered"] = True
with zipfile.ZipFile("auditpack.zip", "w") as z:
    z.writestr("manifest.json", json.dumps(manifest, indent=2, sort_keys=True))
PY

praevisio verify auditpack.zip
```

**Expected:** first verify passes, second verify fails with integrity error.

---

## Example 4 — Hash‑only evidence retention + replay requires artifacts

**Goal:** Show hash‑only mode stores hashes/pointers and fails replay if evidence is missing.

**Steps (from an empty repo):**

```bash
mkdir demo-hashonly && cd demo-hashonly

mkdir -p governance/promises tests
cat > governance/promises/llm-input-logging.yaml <<'YAML'
id: llm-input-logging
statement: "All LLM calls are logged"
YAML

cat > .praevisio.yaml <<'YAML'
evaluation:
  promise_id: llm-input-logging
  threshold: 0.1
  pytest_targets: ["tests/test_smoke.py"]
  semgrep_rules_path: ""
  evidence_retention: hash_only
YAML

cat > tests/test_smoke.py <<'PY'
def test_smoke():
    assert True
PY

praevisio evaluate-commit . --config .praevisio.yaml --json
rm -f .praevisio/runs/*/evidence/*.json
praevisio replay-audit --latest
```

**Expected:** replay fails with “missing evidence artifact”.

---

## Example 5 — Applicability guard (self‑declared not‑applicable is ignored)

**Goal:** Show `applicability_override_ignored` when a promise claims `applicable: false` but evidence applies.

**Steps (from an empty repo):**

```bash
mkdir demo-applicability && cd demo-applicability

mkdir -p governance/promises tests
cat > governance/promises/llm-input-logging.yaml <<'YAML'
id: llm-input-logging
statement: "All LLM calls are logged"
applicable: false
YAML

cat > .praevisio.yaml <<'YAML'
evaluation:
  promise_id: llm-input-logging
  threshold: 0.1
  pytest_targets: ["tests/test_smoke.py"]
  semgrep_rules_path: ""
YAML

cat > tests/test_smoke.py <<'PY'
def test_smoke():
    assert True
PY

praevisio evaluate-commit . --config .praevisio.yaml --json
```

**Expected:** output JSON contains `details.anomalies` with `applicability_override_ignored`, and `details.applicable` is `true`.

---

## Example 6 — Override expiry + compensating controls (fail‑closed)

**Goal:** Demonstrate that overrides require compensating controls and a valid expiry for high‑severity gates.

**Steps (from an empty repo):**

```bash
mkdir demo-override && cd demo-override

cat > override_demo.py <<'PY'
from datetime import datetime, timezone
from praevisio.application.engine import PraevisioEngine
from praevisio.domain.config import Configuration
from praevisio.domain.evaluation_config import EvaluationConfig
from praevisio.domain.entities import EvaluationResult
from praevisio.domain.ports import ConfigLoader, FileSystemService

class DummyConfigLoader(ConfigLoader):
    def load(self, path: str) -> Configuration:
        return Configuration()

class DummyFS(FileSystemService):
    def read_text(self, path: str) -> str: return ""
    def write_text(self, path: str, content: str) -> None: return None

class FakeEval:
    def evaluate_path(self, path: str, *args, **kwargs) -> EvaluationResult:
        return EvaluationResult(credence=0.5, verdict="red", details={"applicable": True})

engine = PraevisioEngine(DummyConfigLoader(), DummyFS(), evaluation_service=FakeEval())
evaluation = EvaluationConfig(promise_id="llm-input-logging", threshold=0.95, severity="high")
now = datetime(2026, 2, 4, tzinfo=timezone.utc)

override_ok = {
    "decision_sha256": "deadbeef",
    "approved_by": "alice",
    "expires_at": "2026-12-31T00:00:00Z",
    "compensating_controls": ["extra_monitoring"],
}
override_bad = {
    "decision_sha256": "deadbeef",
    "approved_by": "alice",
    "expires_at": "2026-12-31T00:00:00Z",
    "compensating_controls": [],
}

ok = engine.ci_gate(".", evaluation, severity="high", fail_on_violation=True, override=override_ok, now=now)
bad = engine.ci_gate(".", evaluation, severity="high", fail_on_violation=True, override=override_bad, now=now)
print("override_ok should_fail:", ok.should_fail, "override_applied:", ok.report_entry.get("override_applied"))
print("override_bad should_fail:", bad.should_fail, "override_applied:", bad.report_entry.get("override_applied"))
PY

python override_demo.py
```

**Expected:** `override_ok` unblocks the gate; `override_bad` does not.

---

## Example 7 — CI gate fail‑closed behavior

**Goal:** Show `ci-gate` enforces policy and returns a non‑zero exit on violation.

**Steps (from an empty repo):**

```bash
mkdir demo-ci-gate && cd demo-ci-gate

mkdir -p governance/promises tests
cat > governance/promises/llm-input-logging.yaml <<'YAML'
id: llm-input-logging
statement: "All LLM calls are logged"
YAML

cat > .praevisio.yaml <<'YAML'
evaluation:
  promise_id: llm-input-logging
  threshold: 0.99
  pytest_targets: []
  semgrep_rules_path: ""
YAML

praevisio ci-gate . --enforce --output logs/ci-gate-report.json --config .praevisio.yaml
```

**Expected:** `ci-gate` exits non‑zero and writes `logs/ci-gate-report.json` explaining the failure.
