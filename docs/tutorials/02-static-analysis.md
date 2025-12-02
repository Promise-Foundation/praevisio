# Tutorial 2 – Static Analysis as Evidence (Semgrep)

## What You'll Learn

In Tutorial 1, you learned the fundamentals of Praevisio: promises, evidence, credence, and verdicts. You saw how a simple test and a basic pattern check could verify that your LLM client logs prompts. That was enough to prove the concept, but it had a significant limitation: the pattern check was crude, looking only for the literal string "log(" anywhere in the file.

In this tutorial, you'll graduate from toy pattern matching to real static analysis using Semgrep, an industrial-strength code analysis tool. You'll learn how to write rules that understand your code's structure, catch violations that simple string searches would miss, and provide much stronger evidence for your promises. By the end, you'll understand why static analysis is such a powerful complement to testing, and how Praevisio uses both together to achieve high-confidence governance.

## Why Static Analysis Matters

Before we dive into Semgrep, let's understand why we need it. The pattern check from Tutorial 1 had several problems. If you moved the logging call to a helper function that didn't have "log" in its name, the pattern check would fail even though your code was actually compliant. If you added a comment that said "remember to log(prompt)", the pattern check would pass even though no actual logging happened. If you had multiple code paths through your function and only some of them logged, the pattern check wouldn't notice.

Real codebases are complex. Functions call other functions. Control flow branches in many directions. The same functionality might be implemented differently in different places. A simple string search can't understand any of this structure—it just looks at the file as a sequence of characters. This makes it brittle and easy to fool, either accidentally or deliberately.

Static analysis tools like Semgrep solve this problem by actually parsing your code and understanding its abstract syntax tree—the structured representation of what your code means, not just what characters it contains. When you write a Semgrep rule to detect unlogged LLM calls, Semgrep understands that it's looking for a function call, knows what the arguments mean, and can track whether there's another function call nearby that would provide the required logging. This understanding makes Semgrep's evidence much more reliable than simple pattern matching.

Moreover, static analysis scales differently than testing. Writing a comprehensive test suite that covers every code path in a large application is expensive and time-consuming. Static analysis, once configured, analyzes your entire codebase in seconds, checking hundreds of functions against your rules automatically. It won't catch everything that tests catch—static analysis can't prove that the logging system actually works when the code runs—but it provides fast, comprehensive coverage that complements the depth of testing.

This complementary relationship is why Praevisio uses both. Tests provide deep, execution-based evidence for specific scenarios. Static analysis provides broad, structure-based evidence across your entire codebase. Together, they give you high confidence that promises are kept.

## The Regulatory Context

Before we write our first Semgrep rule, let's understand why regulators and standards bodies care about the kind of comprehensive checking that static analysis enables.

The NIST AI Risk Management Framework emphasizes two key functions that static analysis supports. First, the "Measure" function requires organizations to track and assess AI risks, including maintaining data and model integrity throughout the system lifecycle. Static analysis helps by continuously verifying that data handling practices—like logging—are consistently applied everywhere they should be. Second, the "Manage" function requires implementing controls to mitigate risks. Static analysis is itself a control mechanism, automatically enforcing that certain patterns are followed everywhere in your code.

ISO/IEC 42001, the emerging international standard for AI management systems, goes further by requiring continuous testing and validation of risk controls. The standard recognizes that compliance isn't a one-time checkbox—it's an ongoing process that must adapt as code changes. Static analysis fits this model perfectly because it runs on every commit, continuously re-verifying that your controls are in place. When you add a new feature that makes LLM calls, static analysis immediately checks whether it follows your logging practices, without waiting for someone to manually write new tests.

These standards reflect a broader shift in how regulators think about software governance. They're moving away from "process compliance" (did you follow the right development process?) toward "outcome verification" (can you prove the code does what you claim?). Static analysis bridges this gap by providing automated, reproducible evidence that specific outcomes—like complete logging coverage—are actually achieved in your code.

## Extending the Promise

For this tutorial, we're going to strengthen the logging promise from Tutorial 1. The original promise said "All LLM API calls must log input prompts," which was a good start. But let's make it more specific to capture what we really need for audit compliance.

Open `governance/promises/llm-logging-complete.yaml` (this is a new promise file that extends what you learned in Tutorial 1):
```yaml
id: llm-logging-complete
version: 0.1.0
domain: /llm/observability
statement: All code paths that send prompts to the LLM must log both the prompt and a trace ID for correlation.
critical: true
success_criteria:
  credence_threshold: 0.95
  evidence_types:
    - procedural
    - static_analysis
  coverage_requirement: 0.95
parameters:
  required_fields:
    - prompt
    - trace_id
  context_window: 5
stake:
  credits: 0
```

Let's examine what's new here compared to Tutorial 1. The statement now explicitly mentions "all code paths," which matters because a function might log in some branches but not others. We've also added a specific requirement for a trace ID alongside the prompt. In real audit scenarios, you need to correlate log entries with requests, and trace IDs make that possible. The promise is saying "not only must you log, but you must log the right information."

The evidence types now include "static_analysis" as an explicit type rather than just "pattern." This tells Praevisio to use a full static analyzer like Semgrep, not just pattern matching. The distinction matters because static analyzers provide structured output that Praevisio can interpret more reliably.

There's a new field: coverage_requirement set to 0.95. This means we're requiring 95% of LLM call sites to have proper logging. Why not 100%? Because in complex codebases, there might be legacy code paths that are scheduled for removal, or test code that doesn't need production logging. The 95% threshold gives you a small buffer for exceptions while still enforcing near-complete coverage. Combined with the credence threshold, this creates a two-layer safety check: at least 95% of call sites must log, and we must be at least 95% confident that this is true.

The parameters section specifies what "proper logging" means. The required_fields list tells Praevisio (and Semgrep) to verify that both prompt and trace_id are being logged, not just one or the other. The context_window of 5 tells the static analyzer to look within 5 lines of code after an LLM call to find the corresponding log statement. This handles cases where there might be a few lines of processing between the LLM call and the logging.

This promise is more sophisticated than Tutorial 1's version, but it's still readable and maintainable. That's the power of Praevisio's promise format: you can express complex requirements precisely without writing pages of policy documents that no one will read or follow.

## Understanding Semgrep

Before we write our first Semgrep rule, let's understand what Semgrep is and how it works. Semgrep is a fast, open-source static analysis tool that lets you write patterns to search code like you would search text, but with awareness of code structure. It supports Python, JavaScript, Go, Java, and many other languages, using the same rule syntax across all of them.

The key insight behind Semgrep is that most code analysis questions can be expressed as pattern matching if your patterns understand syntax. Instead of searching for the string "call_llm(", you write a pattern that matches any function call to something named call_llm, regardless of whitespace, comments, or formatting. Instead of searching for "log(" nearby, you write a pattern that matches any function call that includes specific arguments, checking that it appears within a certain scope.

Semgrep rules are written in YAML and use a special syntax where you write code that looks almost like the code you're searching for. Semgrep parses both your rule and your codebase into abstract syntax trees, then matches the tree structures. This makes the matching robust to superficial code variations while still being precise about what matters.

For example, these are all different strings, but they're all the same function call syntactically:
```python
call_llm(prompt)
call_llm( prompt )
call_llm(
    prompt
)
call_llm(prompt,)  # trailing comma
```

A string-based pattern matcher would need four different patterns to catch all these. A Semgrep rule written once catches all of them because it matches the syntax tree, not the text. This robustness is why static analysis is more reliable than simple pattern matching.

## Writing Your First Semgrep Rule

Now let's write a Semgrep rule that detects unlogged LLM calls. Create a new file at `governance/evidence/semgrep_rules.yaml`:
```yaml
rules:
  - id: llm-call-must-log
    languages:
      - python
    message: LLM call detected without subsequent logging
    severity: ERROR
    patterns:
      - pattern: $CLIENT.call_llm($PROMPT)
      - pattern-not-inside: |
          $CLIENT.call_llm($PROMPT)
          ...
          log($PROMPT, ...)
    metadata:
      category: governance
      promise_id: llm-logging-complete
      evidence_type: static_analysis
```

This rule is where Semgrep's power becomes apparent. Let's break down each section to understand how it works and why it's written this way.

The id field uniquely identifies this rule. When Semgrep finds a violation, it reports this ID so you know which rule was triggered. The languages list tells Semgrep this rule only applies to Python files—Semgrep will skip files in other languages. This matters in polyglot codebases where you might have JavaScript frontend code and Python backend code.

The message is what users see when Semgrep finds a violation. It should be clear and actionable. The severity of ERROR means this is a must-fix issue, not just a suggestion. Semgrep supports WARNING and INFO levels too, which you might use for less critical promises.

Now we get to the interesting part: the patterns section. This is where we define what code structure we're looking for. The first pattern, `$CLIENT.call_llm($PROMPT)`, is a template that matches any method call to call_llm. The dollar signs before CLIENT and PROMPT are metavariables—they match anything in that position and remember what they matched for later use.

So this pattern matches all of these:
```python
client.call_llm(prompt)
self.llm.call_llm(user_query)
api.call_llm("Hello, world")
```

The metavariable $CLIENT matches client, self.llm, and api respectively. The metavariable $PROMPT matches prompt, user_query, and "Hello, world" respectively. Semgrep doesn't care what the actual names or values are—it just cares about the structure of the code.

The second pattern is more sophisticated: pattern-not-inside. This is one of Semgrep's combining operators that let you express "match this pattern BUT NOT if it appears inside this larger pattern." The larger pattern is:
```python
$CLIENT.call_llm($PROMPT)
...
log($PROMPT, ...)
```

The ... is special Semgrep syntax meaning "zero or more statements here." So this pattern matches any code block where a call_llm is followed (possibly after some intervening statements) by a log call that uses the same prompt metavariable.

Putting it together, the rule says: "Find any call_llm invocation, but exclude ones that appear inside a block where the same prompt is later logged." In other words, "find unlogged LLM calls." This is exactly what we want for our promise.

The metadata section at the end contains extra information that Praevisio uses. The category helps organize rules when you have hundreds of them. The promise_id links this rule back to the specific promise it provides evidence for. The evidence_type tells Praevisio that this is static_analysis evidence, which affects how much weight it gets in credence calculations.

This rule is simple but powerful. It will catch unlogged LLM calls across your entire codebase, regardless of where they appear or how they're formatted. And because it's pattern-based, it runs fast—Semgrep can analyze thousands of lines of code per second.

## Creating the Semgrep Adapter

Semgrep rules are powerful, but they're just text files until something runs them and interprets their output. That's where the Semgrep adapter comes in—it's the bridge between Semgrep (an external tool) and Praevisio (which needs structured evidence data).

The adapter's job is to run Semgrep with your rules, parse the JSON output Semgrep produces, and convert it into an evidence score that Praevisio can use in credence calculations. Let's look at the adapter that's provided in your project at `governance/evidence/semgrep_adapter.py`:
```python
import subprocess
import json
from pathlib import Path

def run_semgrep_analysis(target_path: str) -> dict:
    """
    Run Semgrep with governance rules and return structured evidence.
    
    This adapter is responsible for:
    1. Executing Semgrep with the appropriate rules
    2. Parsing Semgrep's JSON output
    3. Computing coverage metrics
    4. Returning evidence in Praevisio's expected format
    
    Returns a dict with:
        - total_llm_calls: number of call_llm invocations found
        - violations: number that lack proper logging
        - coverage: fraction of calls with logging (0.0 to 1.0)
        - findings: list of specific violation locations
    """
    
    rules_path = Path("governance/evidence/semgrep_rules.yaml")
    
    # Run Semgrep with JSON output
    # The --config flag points to our custom rules
    # The --json flag gives us structured output we can parse
    # The target_path tells Semgrep what code to analyze
    result = subprocess.run(
        ["semgrep", "--config", str(rules_path), "--json", target_path],
        capture_output=True,
        text=True
    )
    
    # Semgrep returns exit code 1 when it finds matches, which is expected
    # Only exit code 2+ indicates an actual error
    if result.returncode >= 2:
        raise RuntimeError(f"Semgrep failed: {result.stderr}")
    
    # Parse the JSON output
    output = json.loads(result.stdout)
    
    # Extract findings - each finding represents a violation
    findings = output.get("results", [])
    
    # Count violations by rule
    llm_violations = [
        f for f in findings 
        if f.get("check_id") == "llm-call-must-log"
    ]
    
    # To compute coverage, we need to know total LLM calls
    # We can approximate this by running a separate Semgrep rule
    # that just finds all call_llm invocations, or by counting
    # what we found plus what was flagged
    
    # For this tutorial, we'll use a simple heuristic:
    # Run another Semgrep pass that finds ALL call_llm calls
    count_result = subprocess.run(
        ["semgrep", "--pattern", "$X.call_llm($Y)", "--json", target_path],
        capture_output=True,
        text=True
    )
    
    if count_result.returncode < 2:
        count_output = json.loads(count_result.stdout)
        total_calls = len(count_output.get("results", []))
    else:
        total_calls = len(llm_violations)
    
    # Compute coverage: what fraction of calls have logging?
    # If we found violations, coverage is less than 100%
    num_violations = len(llm_violations)
    
    if total_calls == 0:
        # No LLM calls found at all - this might be test code
        # Return perfect coverage to avoid false negatives
        coverage = 1.0
    else:
        # Coverage = (total - violations) / total
        coverage = (total_calls - num_violations) / total_calls
    
    return {
        "total_llm_calls": total_calls,
        "violations": num_violations,
        "coverage": coverage,
        "findings": [
            {
                "file": f.get("path"),
                "line": f.get("start", {}).get("line"),
                "code": f.get("extra", {}).get("lines", "")
            }
            for f in llm_violations
        ]
    }
```

Let's walk through this adapter carefully because it demonstrates important patterns you'll use when integrating other static analysis tools with Praevisio.

The function signature takes a target_path, which is the directory or file to analyze. This flexibility lets Praevisio analyze a single changed file during a commit, or scan your entire codebase during a full audit. The return type is a dict because we're returning structured evidence with multiple pieces of information.

The first step is locating the rules file. We use Path from Python's pathlib module to construct platform-independent paths. This matters because your governance rules might be checked into git and used by developers on Windows, Mac, and Linux.

Then we actually run Semgrep using subprocess.run. The command line we build is important: the --config flag tells Semgrep where our custom rules are, --json requests machine-readable output instead of human-readable text, and target_path tells Semgrep what code to scan. We capture_output=True to get Semgrep's output, and text=True to get it as a string rather than bytes.

Semgrep's exit codes have specific meanings that the adapter must handle correctly. Exit code 0 means "no findings" (everything is clean). Exit code 1 means "found matches" (violations exist, but Semgrep ran successfully). Exit codes 2 and higher mean "Semgrep itself had an error" (maybe the rules file is malformed, or Semgrep couldn't parse your code). We only treat 2+ as an error because finding violations is actually what we expect—it means Semgrep did its job.

After running Semgrep, we parse the JSON output and extract the results array, which contains one entry for each violation found. Each violation has metadata like the file path, line number, and the actual code that triggered the rule.

Here's where it gets interesting: we filter the findings to only include those from our llm-call-must-log rule. Why? Because in a real system, you might have dozens of Semgrep rules checking different promises. This adapter is specifically providing evidence for the logging promise, so it only counts violations of the logging rule. Other rules would be handled by other adapters or other sections of this adapter.

To compute coverage accurately, we need to know not just how many violations exist, but how many total LLM calls exist in the codebase. The violations tell us what's wrong; the total tells us the scale of what we're checking. We compute this by running Semgrep again with a simple pattern that matches all call_llm invocations, whether they log or not. This second pass is fast because Semgrep is optimized for repeated scanning.

The coverage calculation is straightforward: if we found 2 violations out of 20 total calls, coverage is (20 - 2) / 20 = 0.90 or 90%. This coverage metric becomes one of the key pieces of evidence Praevisio uses in credence calculations. High coverage (say, 0.98) provides strong evidence that the promise is kept. Low coverage (say, 0.60) provides strong evidence that it's not.

There's a subtle edge case we handle: when total_calls is zero, we return coverage of 1.0. This seems counterintuitive—if there are no LLM calls, shouldn't coverage be undefined rather than perfect? But think about what this means practically. If a file has no LLM calls, then vacuously, all LLM calls in that file are properly logged (because there are none to log). Returning 1.0 prevents false negatives where test files or utility modules get flagged for not having logging when they don't need any.

Finally, we structure the findings in a format that's useful for Praevisio and for developers. Each finding includes the file path, line number, and a snippet of the actual code that violated the rule. When credence is low and the verdict is red, Praevisio can show developers exactly where the problems are, not just "somewhere in the codebase." This specificity makes violations actionable.

This adapter pattern—run external tool, parse output, compute metrics, return structured data—is reusable for any static analysis tool you want to integrate with Praevisio. Whether you're using Bandit for security checks, Pylint for code quality, or custom tools, the adapter structure stays the same.

## Updating the Evaluator

Now that we have Semgrep producing evidence, we need to update Praevisio's evaluator to use it. The evaluator from Tutorial 1 only considered test results and a simple pattern check. Now we'll combine test results with real static analysis to compute a more sophisticated credence score.

Open `praevisio/application/services.py` and look at the updated evaluate_commit function:
```python
from praevisio.domain.entities import EvaluationResult
from governance.evidence.semgrep_adapter import run_semgrep_analysis
import pytest
import os

def evaluate_commit(path: str) -> EvaluationResult:
    """
    Evaluate whether a commit satisfies the llm-logging-complete promise.
    
    This version combines multiple evidence sources:
    1. Pytest results (procedural evidence)
    2. Semgrep static analysis (static_analysis evidence)
    
    Each evidence source contributes to credence based on its strength.
    """
    
    # Gather evidence 1: Run the test suite
    # Pytest returns 0 for all tests passing, nonzero otherwise
    test_result = pytest.main([
        "app/tests/test_logging.py",
        "-v",  # verbose output
        "--tb=short"  # short traceback on failure
    ])
    test_passes = (test_result == 0)
    
    # Gather evidence 2: Run Semgrep analysis
    semgrep_evidence = run_semgrep_analysis(path)
    
    # Extract key metrics from Semgrep
    coverage = semgrep_evidence["coverage"]
    total_calls = semgrep_evidence["total_llm_calls"]
    violations = semgrep_evidence["violations"]
    
    # Now compute credence by weighting the evidence sources
    # 
    # Tests are strong evidence but limited in scope (they only check
    # the specific scenarios we wrote tests for).
    # 
    # Semgrep is comprehensive (it checks the whole codebase) but can't
    # verify runtime behavior.
    # 
    # We weight them to reflect their complementary strengths:
    # - Tests get 40% weight
    # - Semgrep coverage gets 60% weight
    
    test_contribution = 0.4 if test_passes else 0.0
    semgrep_contribution = 0.6 * coverage
    
    # Base credence from evidence
    credence = test_contribution + semgrep_contribution
    
    # Apply modifiers based on the evidence details
    
    # Modifier 1: If tests fail, cap credence at 0.70 regardless of
    # static analysis. This reflects that failing tests are strong
    # evidence of problems even if static analysis looks good.
    if not test_passes:
        credence = min(credence, 0.70)
    
    # Modifier 2: If coverage is below the promise requirement (0.95)
    # by more than 10%, apply a penalty. This reflects that even if
    # tests pass, widespread violations indicate systemic problems.
    if coverage < 0.85:
        credence *= 0.90  # 10% penalty
    
    # Modifier 3: If we found zero LLM calls, we might be analyzing
    # the wrong code or test code. Don't penalize this case.
    if total_calls == 0:
        # Assume this is test/utility code without LLM calls
        # Return neutral evidence rather than false positive
        credence = 0.80
    
    # Compute verdict
    verdict = "green" if credence >= 0.95 else "red"
    
    # Add detailed diagnostic info that Praevisio can display
    details = {
        "test_passes": test_passes,
        "semgrep_coverage": coverage,
        "total_llm_calls": total_calls,
        "violations_found": violations,
        "test_contribution": test_contribution,
        "semgrep_contribution": semgrep_contribution,
        "finding_details": semgrep_evidence["findings"]
    }
    
    return EvaluationResult(
        credence=credence,
        verdict=verdict,
        details=details
    )
```

This evaluator demonstrates several important principles in evidence fusion—the process of combining multiple evidence sources into a single credence score. Let's examine each principle and understand why the code is structured this way.

First, we gather both evidence sources independently. The tests run without knowing what Semgrep found, and Semgrep analyzes code without knowing if tests exist. This independence is important because it prevents one evidence source from contaminating another. If tests somehow depended on Semgrep's output, we'd be double-counting the same information.

The weighting scheme—40% for tests, 60% for Semgrep—reflects the relative strengths of each evidence type. Tests provide deep, execution-based verification but only for the scenarios we explicitly wrote tests for. If we have three test cases but the code has ten different LLM call sites, tests only directly verify 30% of the codebase. Semgrep, on the other hand, checks every single LLM call automatically. Its breadth deserves more weight than tests' depth in this context.

These weights aren't arbitrary or magic numbers. They're based on empirical observations about what correlates with actual compliance in real codebases. A research team analyzing governance violations might find that when tests pass and Semgrep shows 95% coverage, the code is actually compliant in 97% of cases (hence credence of 0.97). When tests pass but coverage is only 80%, actual compliance might be only 70%. The weights encode these correlations.

Different organizations might choose different weights based on their own data and risk tolerance. A team with extremely thorough tests might weight them 60% and Semgrep 40%. A team with sparse tests but comprehensive static analysis might use 30%/70%. Praevisio lets you configure these weights because there's no universal "correct" answer—it depends on the quality of your evidence sources.

The modifiers add nuance to the basic weighted sum. The first modifier—capping credence at 0.70 when tests fail—reflects an important asymmetry: failing tests are stronger negative evidence than passing tests are positive evidence. If a test explicitly checks that logging happens and the test fails, we know something is wrong even if static analysis says everything looks fine. Maybe the logging call exists but is broken, or maybe the test is checking a different code path than static analysis examined. Either way, we can't have high confidence when tests fail.

The second modifier penalizes systematically low coverage. If Semgrep finds that only 60% of LLM calls have logging, even passing tests can't overcome that. The tests might be checking the 60% that works while missing the 40% that doesn't. The 10% penalty (multiplying by 0.90) reflects this concern without being so harsh that one or two violations cause complete failure.

The third modifier handles an edge case that would otherwise cause false positives: code with no LLM calls at all. Imagine running the evaluator on a utility module that just has helper functions. There are no LLM calls, so technically coverage is undefined or maybe 100% (vacuously true). We return credence of 0.80 in this case—neither failing nor passing strongly, just "not applicable." This prevents the evaluator from wasting time on irrelevant code.

The details dictionary at the end is crucial for debuggability. When a developer commits code and gets a red verdict, they need to know why. Is it because tests failed? Because coverage was low? Because there were violations? The details provide this diagnostic information, which Praevisio displays in its output. Good governance tools don't just say "no," they say "no, because X and Y, and here's where to fix it."

This evaluator structure—gather evidence, weight it, apply modifiers, compute verdict, provide details—is a pattern you'll use for increasingly complex promises as you advance through the tutorials. The specifics change, but the structure remains the same.

## Running the Enhanced Evaluation

Now let's see the improved evaluator in action. Make sure your LLM client from Tutorial 1 still has proper logging (the `self._log_prompt(prompt)` line is uncommented), then run:
```bash
praevisio evaluate-commit ./
```

You should see output like:
```
Evaluating promise: llm-logging-complete
Gathering evidence...
  ✓ Procedural evidence: test_logging.py passed (2/2 tests)
  ✓ Static analysis: Semgrep found 1 LLM call, 0 violations
  
Evidence summary:
  Test contribution: 0.40
  Semgrep contribution: 0.60 (coverage: 1.00)
  
Credence: 1.00
Verdict: green
```

Notice how much more informative this output is compared to Tutorial 1. You can see exactly how many tests passed, how many LLM calls Semgrep found, and how each evidence source contributed to the final credence. The coverage of 1.00 means Semgrep found proper logging for 100% of LLM call sites.

Let's try something interesting: add a second LLM call to your client that doesn't log. Open `app/src/llm_client.py` and add this method:
```python
def generate_unlogged(self, prompt: str) -> str:
    """A second method that violates the logging promise."""
    return "This call doesn't log anything."
```

Now run the evaluation again:
```bash
praevisio evaluate-commit ./
```

You should see:

Evaluating promise: llm-logging-complete
Gathering evidence...
✓ Procedural evidence: test_logging.py passed (2/2 tests)
✗ Static analysis: Semgrep found 2 LLM calls, 1 violation
Evidence summary:
Test contribution: 0.40
Semgrep contribution: 0.30 (coverage: 0.50)
Violations found:

app/src/llm_client.py:25: generate_unlogged() missing log call

Credence: 0.70
Verdict: red

This is where static analysis shines. The tests still pass because they only check the original generate method, which still logs properly. But Semgrep scanned the entire file, found both LLM call sites, and detected that the new method doesn't log. Coverage dropped to 0.50 (one out of two calls has logging), which reduced the Semgrep contribution from 0.60 to 0.30. The final credence of 0.70 is below the threshold of 0.95, so the verdict is red.

Moreover, Praevisio tells you exactly where the problem is: line 25 in llm_client.py, in the generate_unlogged method. You don't need to search through your entire codebase to find the violation. This specificity is what makes static analysis practical for large projects.

Remove the generate_unlogged method (or add logging to it) and verify that the verdict returns to green. This demonstrates the cycle you'll follow in real development: make changes, run evaluation, see what's wrong, fix it, re-evaluate.

## Understanding Coverage vs. Credence

At this point, you might be wondering: if Semgrep reports 100% coverage, why isn't credence 1.00 always? And if coverage is 50%, why isn't credence 0.50? Let's clarify the relationship between these two numbers because it's subtle but important.

Coverage is a measurement from a single evidence source (Semgrep). It tells you what fraction of LLM calls Semgrep found to have proper logging. Coverage of 1.00 means "according to static analysis, every call site has logging." Coverage of 0.50 means "static analysis found logging at half the call sites."

But coverage doesn't tell you how reliable the measurement is. Maybe Semgrep's rules have bugs and miss some cases. Maybe the logging exists but is disabled by a configuration flag that Semgrep doesn't know about. Maybe there are call sites that Semgrep didn't find because they're generated dynamically. Coverage is a single measurement, and single measurements can be wrong.

Credence, by contrast, is your overall confidence that the promise is kept, accounting for all evidence sources and their reliabilities. Even if Semgrep reports perfect coverage, credence might be 0.97 rather than 1.00 because we're not 100% certain that Semgrep found everything. Conversely, even if coverage is only 85%, credence might be 0.88 if tests provide strong supporting evidence that the missing 15% isn't critical.

This is why Praevisio uses multiple evidence sources. If only Semgrep said coverage was 100%, we'd be less confident than if both Semgrep said 100% and tests confirmed that the logging works when code runs. Multiple independent sources of evidence, even if each is imperfect, combine to give higher confidence than any single source could provide alone.

Think of it like a criminal trial. One eyewitness saying they saw the defendant at the scene is evidence, but it might be mistaken identity. Two independent eyewitnesses who don't know each other saying the same thing is much stronger evidence because the chance that both are wrong is low. Semgrep and tests are like independent witnesses—they look at the code in completely different ways (static structure vs. runtime execution), so when they agree, we can be highly confident.
The evaluator weights reflect this reasoning. When both Semgrep shows 100% coverage and tests pass, credence is very high (approaching 1.0). When they disagree—Semgrep says 100% but tests fail, or tests pass but coverage is low—credence drops because something seems inconsistent and we don't know which evidence source to trust more.
What Makes Good Static Analysis Evidence
As you start writing your own Semgrep rules for other promises, you'll need to understand what makes static analysis evidence valuable. Not all Semgrep rules provide equally useful evidence. Let's discuss the characteristics of good rules.
Good rules are precise: they match exactly what you care about and nothing else. A rule that flags all function calls as potential violations wouldn't be useful because the false positive rate would be too high. Your rule specifically looks for call_llm invocations without corresponding log calls, which is precisely what the promise requires.
Good rules are comprehensive: they catch all the patterns you need to catch. If your rule only checks direct function calls but misses calls through wrapper functions or method aliases, you'll get false negatives (violations that slip through). As you learn more about your codebase's patterns, you'll refine rules to cover more cases.
Good rules are stable: they shouldn't produce different results on the same code just because you run them at different times. This stability is automatic with static analysis (unlike flaky tests that depend on timing or external services), which makes it ideal for governance. You can re-run the evaluation on last week's commit and get the same credence as you got last week.
Good rules provide actionable output: when a rule matches, the finding should tell developers what to fix. Your rule's message "LLM call detected without subsequent logging" combined with the line number gives developers exactly what they need. A vague message like "potential issue detected" wouldn't help anyone.
Good rules have appropriate scope: they analyze the right amount of code. A rule that only checks one function wouldn't provide good evidence about your entire codebase. A rule that analyzes every file in your project, including vendored third-party libraries, might produce noise from code you don't control. Your rule looks at your application code, which is the right scope for this promise.
As you write more rules, you'll develop intuition for what works. Start with simple patterns that catch the most common violations, then refine them as you learn what edge cases exist in your codebase. Praevisio's credence framework is forgiving of imperfect rules because it combines multiple evidence sources—a rule with a 5% false positive rate can still contribute useful evidence when combined with tests.
The Power of Automated Evidence
Let's step back and appreciate what you've built. Every time you commit code, Praevisio now automatically:
Runs your test suite and records which tests passed. Launches Semgrep and scans your entire codebase for logging violations. Computes coverage metrics showing what percentage of call sites have proper logging. Combines these evidence sources with appropriate weights to compute credence. Compares credence to your threshold and issues a verdict. Provides detailed diagnostics showing exactly where problems exist if any.
All of this happens in seconds, requires no manual intervention, and produces quantitative, comparable results. This automation is what makes comprehensive governance practical at scale.
In a manual code review, a reviewer might spend 30 minutes examining a pull request, check three or four files carefully, skim the rest, and miss violations in code they didn't look at closely. They're human, they get tired, they have deadlines. Even the best reviewer can't match the comprehensiveness of static analysis that literally checks every line in seconds.
But static analysis alone isn't enough, which is why tests matter. Static analysis can tell you "this call site doesn't have a logging statement nearby," but it can't tell you "when you run this code, the logging actually happens and writes to the right place." Tests provide that runtime verification. Together, static analysis and tests cover both structural compliance (is the right code present?) and behavioral compliance (does the code work correctly?).
This is the essence of evidence-driven governance: use multiple automated tools, each checking what it's good at checking, and combine their outputs mathematically to reach an overall confidence level. It's more reliable than manual review, faster than comprehensive testing, and more sophisticated than simple rule checking.
Next Steps
In Tutorial 3, you'll add a third evidence source: git history analysis. You'll learn how to use patterns in your commit history—how often developers forget to add logging when adding LLM calls, how often logging is later removed, whether certain files or developers have better track records—as evidence for current compliance. This historical evidence complements the snapshot view that tests and static analysis provide, giving you temporal context about how reliably promises are kept over time.
You'll also learn about evidence weighting schemes that adapt based on evidence quality, and how Praevisio's confidence scores (different from credence) tell you how stable your credence estimate is. If you've only gathered one piece of weak evidence, confidence is low even if credence happens to be high. If you've gathered five pieces of strong, agreeing evidence, confidence is high. Understanding this distinction helps you know when to gather more evidence versus when you can confidently commit.
For now, make sure you understand how Semgrep rules work, how the adapter converts Semgrep output into evidence, and how the evaluator weighs different evidence types. Try writing a second Semgrep rule for a different promise—maybe one that checks that sensitive data is masked, or that certain functions are never called from certain contexts. The pattern is the same, and practicing it now will make Tutorial 3 easier.
Congratulations on leveling up from simple pattern matching to real static analysis. You've just made your governance checks significantly more powerful and reliable.
