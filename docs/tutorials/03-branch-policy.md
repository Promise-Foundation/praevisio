# Tutorial 3 – CI + Branch Policy: Turning Promises into Gates

## What You'll Learn

In Tutorials 1 and 2, you ran Praevisio locally on your machine. You typed `praevisio evaluate-commit`, saw a verdict, and that was it. The system told you whether your code kept its promises, but it was still just a suggestion—nothing actually stopped you from committing code that violated promises.

In this tutorial, we're going to change that. You'll connect Praevisio to your team's deployment pipeline so that broken promises actually block code from reaching production. Specifically, you'll learn how to:

- Set up a GitHub Actions workflow that runs Praevisio on every pull request
- Configure branch protection so that pull requests can't be merged unless Praevisio approves them
- See what happens when someone tries to merge code that violates a high-severity promise (spoiler: it gets blocked)
- Understand why this matters for compliance with standards like NIST AI RMF and the EU AI Act

By the end, you'll have transformed Praevisio from "a tool that gives advice" into "a gate that enforces rules." This is the difference between governance theater and actual governance.

## Why This Matters: From Reporting to Enforcement

Let's start with a scenario that plays out constantly in software teams. Your company has a policy that says "all LLM calls must be logged." Someone writes that policy, it gets approved by legal and compliance, everyone nods in agreement, and then... nothing happens.

Developers don't intentionally ignore the policy. They just forget about it when they're focused on shipping a feature under a deadline. Code reviewers miss violations because they're checking for bugs and performance issues, not governance compliance. The violation makes it to production. Six weeks later, during an audit, someone discovers that 20% of your LLM calls aren't being logged. Now you have an expensive problem.

This happens because the policy lived in a document somewhere, but it wasn't connected to your deployment process. There was no moment where the system checked "does this code follow the policy?" and blocked deployment if the answer was no.

Praevisio solves this by making promises into gates. When you configure a promise as high-severity and connect Praevisio to your CI system, you create a checkpoint that every code change must pass through. If the code doesn't keep its promises, the checkpoint fails, and the code can't be merged. It's not about trusting developers to remember the rules—it's about making it impossible to accidentally break them.

This shift from "reporting on compliance" to "enforcing compliance" is what regulatory frameworks are increasingly demanding. The NIST AI Risk Management Framework talks about the "Manage" function: taking your risk measurements and using them to make operational decisions. The EU AI Act requires continuous monitoring and corrective action before deployment. Both of these mean the same thing: your governance metrics need to actually control what gets deployed, not just describe it after the fact.

## Understanding High-Severity Promises

Before we set up the gate, we need to understand which promises should block deployments and which shouldn't. Not all governance requirements are equally critical. Some are "nice to have" guidelines, while others are "must have" requirements that you can't compromise on.

Praevisio lets you mark promises with a severity level. For this tutorial, we're going to work with high-severity promises—these are the ones that are so important that violating them should stop a deployment.

Think about what makes a promise high-severity in your context:

**Regulatory requirements** - If the EU AI Act says you must log all LLM calls, that's high-severity. Breaking it could result in fines or being barred from operating in Europe.

**Safety-critical behaviors** - If your LLM is used in healthcare and a promise ensures it doesn't give medical advice without disclaimers, that's high-severity. Someone could get hurt.

**Audit requirements** - If your company is SOC2 certified and logging is part of that certification, it's high-severity. Losing certification affects customer trust and contracts.

**Irreversible actions** - If a promise prevents your system from permanently deleting user data without confirmation, that's high-severity. You can't undo a mistake.

Lower-severity promises might include things like code documentation completeness or optimization best practices. Important, but not deployment-blocking.

For this tutorial, we're treating the `llm-input-logging` promise from Tutorials 1 and 2 as high-severity. The reasoning: in a real system, unlogged LLM calls create audit gaps that could violate regulatory requirements. That makes it deployment-blocking.

## Setting Up Your Promise for CI Enforcement

Open the promise file you've been working with: `governance/promises/llm-input-logging.yaml`. We're going to add one new field that marks this promise as high-severity:
```yaml
id: llm-input-logging
version: 0.1.0
domain: /llm/observability
statement: All LLM API calls must log input prompts.
severity: high  # <- This is the new line
critical: true
success_criteria:
  credence_threshold: 0.95
  evidence_types:
    - procedural
    - pattern
parameters: {}
stake:
  credits: 0
```

That `severity: high` line is what tells the CI gate that this promise is deployment-blocking. When Praevisio runs in CI mode, it will look for all high-severity promises and enforce them.

You might notice we already had `critical: true` in the promise. What's the difference between critical and severity? Good question. The `critical` flag controls what happens when you run Praevisio locally—if true, a violation blocks your commit. The `severity` field controls what happens in CI—only high-severity promises block merges to protected branches. You can have a promise that's critical locally but not high-severity (maybe you want developers to fix it before committing, but you'll allow exceptions in emergencies). Or vice versa.

For most important promises, you'll want both set: `critical: true` and `severity: high`. That ensures consistency between what developers see locally and what CI enforces.

## Installing the Praevisio GitHub Action

Praevisio provides a pre-built GitHub Action that makes CI integration straightforward. You don't need to write custom scripts or figure out how to run Praevisio in a CI environment—the action handles all of that.

Create a new file in your repository at `.github/workflows/praevisio-ci.yml`:
```yaml
name: Praevisio Governance Gate

on:
  pull_request:
    branches:
      - main
      - develop

jobs:
  governance-check:
    runs-on: ubuntu-latest
    
    steps:
      - name: Check out code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          
      - name: Install Praevisio
        run: |
          pip install praevisio
          
      - name: Run Governance Gate
        run: |
          praevisio ci-gate \
            --severity high \
            --fail-on-violation \
            --output logs/ci-gate-report.json
            
      - name: Upload Gate Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: praevisio-gate-report
          path: logs/ci-gate-report.json
```

Let's walk through what this workflow does, because understanding each step will help you customize it for your needs.

The `on` section at the top defines when this workflow runs. We've configured it to run on pull requests targeting `main` or `develop` branches. This means every PR that wants to merge into these protected branches gets checked. You might have different branch names in your organization—adjust accordingly.

The workflow runs on `ubuntu-latest`, which is a standard GitHub Actions runner with Python pre-installed. For most projects, this is all you need. If you have special requirements (like GPU access for running model tests), you'd change this to a different runner type.

The first step checks out your code using the standard GitHub checkout action. This gives the workflow access to your repository's files, including your promises, your application code, and your tests.

The second step sets up Python 3.11. Praevisio requires Python 3.10 or higher. If your project uses a different Python version, change this, but make sure it's compatible with Praevisio.

The third step installs Praevisio from PyPI. In a production setup, you might want to pin to a specific version: `pip install praevisio==0.2.1` to ensure consistency. For this tutorial, installing the latest version is fine.

Now we get to the important part: the "Run Governance Gate" step. This is where Praevisio actually evaluates your code. Let's break down the command:

`praevisio ci-gate` is the special command for CI environments. It's different from `praevisio evaluate-commit` that you've been using locally. The CI gate command is designed to:
- Look for all promises with the specified severity level
- Evaluate each one
- Fail the job (exit code 1) if any violations are found
- Produce a machine-readable report

The `--severity high` flag tells Praevisio to only check high-severity promises. You could also use `--severity critical` or `--severity all` depending on what you want to enforce. For now, we're only enforcing high-severity promises.

The `--fail-on-violation` flag ensures that if any high-severity promise has credence below its threshold, the entire CI job fails. This is what makes the gate actually block merges—GitHub won't let you merge a PR with failing required checks.

The `--output` flag tells Praevisio to write a detailed JSON report of what it found. This report includes credence scores, which evidence was collected, and exactly which promises passed or failed. This is invaluable for debugging when a PR is blocked.

The final step uploads the gate report as a GitHub Actions artifact. The `if: always()` condition ensures this happens even if the previous step failed (which it will when promises are violated). This means that even when your PR is blocked, you can download the report and see exactly why.

## Configuring Branch Protection

Installing the workflow is only half the battle. If you stop here, the workflow will run and might even fail, but GitHub will still let you merge the PR anyway. That defeats the whole purpose—we want the workflow failure to actually prevent merging.

This is where GitHub's branch protection rules come in. Branch protection lets you say "you can't merge to this branch unless certain conditions are met." We're going to make the Praevisio governance check one of those conditions.

Here's how to set it up:

1. Go to your repository on GitHub
2. Click "Settings" (you need admin permissions for this)
3. Click "Branches" in the left sidebar
4. Click "Add rule" under "Branch protection rules"
5. In "Branch name pattern," type `main`
6. Check "Require status checks to pass before merging"
7. In the search box that appears, type "governance-check"
8. Select "governance-check" from the list
9. Check "Require branches to be up to date before merging"
10. Click "Create" at the bottom

What did we just do? We told GitHub: "For the main branch, before any PR can be merged, the `governance-check` status must be green. And the PR must be up-to-date with main (no one else's changes merged in the meantime)."

Now when someone opens a PR, GitHub will run your Praevisio workflow. If any high-severity promise is violated, the workflow fails, the status check turns red, and the merge button is disabled. The developer sees a message like:
```
❌ Some checks were not successful
1 failing check
  governance-check — Process completed with exit code 1.
```

They can't merge until they fix the violation and the check passes.

This is enforcement. This is what turns a governance policy from a suggestion into a requirement.

## Seeing the Gate in Action

Let's see what happens when someone tries to merge code that violates a promise. We're going to simulate this by creating a new branch with broken logging and opening a PR.

First, create a new branch:
```bash
git checkout -b test-broken-logging
```

Now open `app/src/llm_client.py` and comment out the logging line, just like you did in Tutorial 1:
```python
def generate(self, prompt: str) -> str:
    # self._log_prompt(prompt)  # Oops, commented out
    return "This is a placeholder response."
```

Commit this change:
```bash
git add app/src/llm_client.py
git commit -m "Test: remove logging to see gate fail"
git push origin test-broken-logging
```

Now go to GitHub and open a pull request from `test-broken-logging` to `main`.

Within a few seconds, you'll see the GitHub Actions workflow start. It will show up as a yellow dot next to your commit, then it will turn red. If you click on the "Details" link next to the failed check, you'll see the workflow logs, which will look something like this:
```
Run Governance Gate
[praevisio][ci-gate] Checking high-severity promises...
[praevisio][ci-gate] Found 1 high-severity promise: llm-input-logging
[praevisio][ci-gate] Gathering evidence...
  ✗ Procedural evidence: test_logging.py failed
  ✗ Static analysis: no logging detected

[praevisio][ci-gate] Credence: 0.12 (threshold: 0.95)
[praevisio][ci-gate] Verdict: RED

[praevisio][ci-gate] ❌ GATE FAILED
High-severity promise llm-input-logging not satisfied.
Violations found:
  - app/src/llm_client.py:15: generate() missing log call

Fix these violations before merging.
Error: Process completed with exit code 1.
```

Back on the pull request page, you'll see:
```
❌ All checks have failed
Review required changes below
  ❌ governance-check — Process completed with exit code 1
  
⚠️ Merging is blocked
The base branch requires all status checks to pass
```

The merge button will be grayed out or missing entirely. You physically cannot merge this PR until the check passes.

Now, still on your `test-broken-logging` branch, restore the logging line:
```python
def generate(self, prompt: str) -> str:
    self._log_prompt(prompt)  # Restored
    return "This is a placeholder response."
```

Commit and push:
```bash
git add app/src/llm_client.py
git commit -m "Fix: restore logging"
git push origin test-broken-logging
```

GitHub will automatically run the workflow again. This time it should pass:
```
Run Governance Gate
[praevisio][ci-gate] Checking high-severity promises...
[praevisio][ci-gate] Found 1 high-severity promise: llm-input-logging
[praevisio][ci-gate] Gathering evidence...
  ✓ Procedural evidence: test_logging.py passed
  ✓ Static analysis: logging detected

[praevisio][ci-gate] Credence: 0.97 (threshold: 0.95)
[praevisio][ci-gate] Verdict: GREEN

[praevisio][ci-gate] ✅ GATE PASSED
All high-severity promises satisfied.
```

On the PR page:
```
✓ All checks have passed
  ✓ governance-check — Process completed with exit code 0
  
This branch has no conflicts with the base branch
Merge pull request
```

The merge button is now active. You can merge the PR.

This is the complete workflow: write code → open PR → Praevisio evaluates → gate fails if violations → fix violations → gate passes → merge allowed.

## Understanding What Just Happened

Let's step back and understand what this gate is actually doing from a governance perspective.

When you run Praevisio locally with `praevisio evaluate-commit`, you're getting advisory information. The tool is helping you catch problems early, but it can't force you to fix them. You could ignore the red verdict and commit anyway (though you shouldn't).

When Praevisio runs in CI as a required status check, it has teeth. The gate is making a binary decision: "Does this code meet our high-severity governance requirements?" If yes, it can proceed to the next stage (merging to main, deploying to production, whatever comes after). If no, it stops here.

This maps directly to what governance standards are asking for. The NIST AI Risk Management Framework talks about the "Manage" function—taking risk measurements and using them to control operational decisions. That's exactly what the CI gate does. The risk measurement is credence (how confident are we that this promise is kept?). The operational decision is the merge gate (can this code be merged?).

The EU AI Act requires continuous monitoring and corrective action before deployment. The CI gate provides both. Every PR is monitored (Praevisio runs on every one). Corrective action is enforced (you must fix violations before merging). And it all happens before deployment, not after.

You can now point to this setup in an audit and say: "Here's our promise about LLM logging. Here's the evidence we collect. Here's how we compute credence. And here's the technical control that prevents non-compliant code from reaching production—it's the required status check on our main branch."

That's a much stronger compliance story than "we have a policy document and we hope developers follow it."

## Customizing the Gate for Your Needs

The setup we've built is intentionally simple—one workflow, one severity level, one protected branch. Real organizations will need more sophisticated configurations. Let's discuss some common customizations.

**Multiple severity levels:** You might want different enforcement for different branches. For example:
- On feature branches: warn about all promises but don't block
- On develop: block on high-severity promises
- On main: block on high and critical promises

You'd do this by creating multiple workflow files with different `--severity` flags and different branch triggers.

**Selective promise enforcement:** Maybe you have 20 promises but only 5 of them should block merges right now. You can create a configuration file that lists exactly which promise IDs are deployment-blocking:
```yaml
# governance/ci-config.yaml
enforcement:
  blocking_promises:
    - llm-input-logging
    - pii-masking
    - output-filtering
```

Then pass this to the CI gate: `praevisio ci-gate --config governance/ci-config.yaml`

**Environment-specific promises:** Your staging environment might have different requirements than production. You could have different promise files for each:
- `governance/promises/staging/` - less strict thresholds
- `governance/promises/production/` - strict thresholds

The CI workflow for staging would point to the staging promises, and production would use production promises.

**Escape hatches for emergencies:** Sometimes you need to merge code that violates a promise because there's an emergency (production is down, security vulnerability needs patching). You can set up an escape hatch using GitHub's "bypass branch protection" permission, which lets designated people merge even when checks fail. But they have to explicitly confirm they're doing it, which creates an audit trail.

**Gradual rollout:** If you're adding Praevisio to an existing codebase with lots of violations, you might not want to block all merges immediately. You could:
1. First, run Praevisio in advisory mode (workflow runs but doesn't block merges)
2. Track the violation rate for a few weeks
3. Once violations drop below 10%, make the check required
4. Gradually tighten thresholds as the codebase improves

This gives your team time to adapt without grinding development to a halt.

## Troubleshooting Common Issues

When you first set up the CI gate, you might encounter some issues. Here are the most common ones and how to fix them.

**Issue: The workflow doesn't run at all**

Check that your workflow file is in `.github/workflows/` and has a `.yml` or `.yaml` extension. Check that the `on` triggers match your PR's target branch. Look at the "Actions" tab in GitHub to see if there are any workflow errors.

**Issue: The workflow runs but doesn't fail when it should**

Make sure you have `--fail-on-violation` in the command. Without this flag, Praevisio will report violations but exit with code 0 (success), so GitHub thinks the check passed.

**Issue: The merge button is still active even though the check failed**

You probably haven't configured branch protection correctly. Go back to Settings → Branches and verify that "Require status checks to pass before merging" is checked and "governance-check" is selected in the list of required checks.

**Issue: Praevisio fails with "No high-severity promises found"**

Make sure at least one promise has `severity: high` in its YAML file. If you recently added that line, make sure you committed the change to the branch that the PR is targeting (usually main).

**Issue: The gate blocks even though violations are fixed**

The PR branch might not be up-to-date with the base branch. Click "Update branch" on the PR page to merge in the latest changes from main, then the workflow will run again.

**Issue: Evidence collection fails in CI but works locally**

This usually means a tool that Praevisio needs (like Semgrep or pytest) isn't installed in the CI environment. Add installation steps to your workflow file before the "Run Governance Gate" step.

## The Bigger Picture: Gates as Infrastructure

What you've built in this tutorial might seem simple—a workflow file and a branch protection rule—but you've actually implemented something profound: governance as infrastructure.

Traditional governance is manual. A compliance officer writes a policy, sends it to the team, hopes everyone reads it, and periodically audits to see if anyone followed it. Violations are discovered after the fact. Fixing them is expensive.

What you've built is automated enforcement. The policy is encoded as a promise. The enforcement mechanism is the CI gate. Violations are detected before merge, when they're cheap to fix. And the whole thing runs automatically—no one has to remember to check.

This is what modern regulatory frameworks are pushing toward. They're tired of companies having beautiful policy documents that no one follows. They want evidence that requirements are actually enforced in the deployment process. The CI gate provides that evidence.

It also changes the culture of governance in your organization. Instead of governance being "those annoying compliance people who slow us down," it becomes "the automated checks that caught a bug before it reached production." Developers start seeing Praevisio as a helpful tool, not an obstacle.

And because the gate is transparent—anyone can see exactly which promises are being enforced and what evidence is required—there's no ambiguity. You can't accidentally violate a requirement you didn't know about. The system tells you what it needs, and if you provide it, you can ship.

## What You've Accomplished

Let's review what you learned in this tutorial:

You understand the difference between advisory governance (local checks) and enforced governance (CI gates). Advisory tools help; gates prevent.

You know how to mark promises as high-severity so they're included in CI enforcement. This lets you distinguish "nice to have" from "must have."

You can set up a GitHub Actions workflow that runs Praevisio on every pull request and fails if high-severity promises aren't satisfied.

You can configure branch protection rules to make that workflow a requirement for merging. This turns the check from advisory to mandatory.

You've seen the complete enforcement flow: write code → PR → gate evaluates → violations block merge → fix → merge allowed.

You understand how this maps to regulatory requirements like NIST AI RMF and EU AI Act. Your gate is evidence of continuous monitoring and corrective action.

Most importantly, you've seen why this matters. You've transformed Praevisio from "a tool that gives you information" into "a gate that controls what ships." That's the difference between governance theater and real governance.

## Next Steps

In Tutorial 4, you'll level up your evidence sources by adding adversarial testing for LLM safety. You'll learn how to use red-teaming tools like Promptfoo to test whether your LLM can be jailbroken, and you'll add those results as evidence for a new promise about safety. This is where things get interesting, because jailbreak resistance is inherently probabilistic—you can't prove your system will never be jailbroken, only that it resists X% of attacks. Praevisio's credence framework is designed for exactly this kind of uncertainty.

For now, make sure you understand the CI gate workflow you just built. Try opening a PR that violates a promise and verify that it gets blocked. Try fixing the violation and verify that the gate then passes. Try changing the threshold in a promise file and see how that affects the gate. The more you experiment with this setup, the more comfortable you'll be adapting it to your organization's needs.

You've just implemented enforcement that most organizations talk about but never actually build. Your governance metrics now control your deployment process. That's not a small achievement—that's the foundation of trustworthy AI governance.
