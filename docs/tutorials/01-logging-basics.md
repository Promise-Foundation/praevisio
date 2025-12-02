# Tutorial 1 – Hello World: Logging & Credence

## What You'll Learn

In this tutorial, you'll use Praevisio to verify your first compliance requirement: that all LLM API calls log their input prompts. By the end, you'll understand how Praevisio transforms a governance policy into an automated, quantifiable check that runs every time you commit code.

This tutorial assumes you already have Praevisio installed and a basic project structure set up. If you haven't installed Praevisio yet, follow the installation guide in the main documentation before proceeding.

## Why Logging Matters

Imagine your team deploys an AI feature to production. Six weeks later, during an audit, you discover that 15% of LLM calls were never logged—violating both your internal policy and regulatory requirements. The cost: expensive remediation, potential fines, and lost trust.

This scenario plays out constantly in AI governance today. Organizations write policies, developers try to follow them, but the gap between "what we said we'd do" and "what the code actually does" only becomes visible after deployment, when it's 10-100x more expensive to fix.

Praevisio inverts this paradigm. Instead of discovering violations weeks later, you catch them at commit time—in seconds, not weeks, and for essentially zero cost. This tutorial shows you how.

## The Regulatory Context

The European Union's AI Act (Articles 12 and 19) requires that high-risk AI systems maintain detailed logs throughout their operational lifetime. Similarly, NIST's AI Risk Management Framework emphasizes that traceability and event logging form the foundation of measurable risk information.

These aren't arbitrary bureaucratic requirements. They exist because when AI systems fail, investigators need to reconstruct what happened. Without logs, that's impossible. Logging is the black box recorder for AI systems—and regulators know it.

Praevisio helps you satisfy these requirements by making logging compliance automatic and verifiable. Instead of hoping developers remember to add logging, you define it as a promise that the system checks on every commit.

## Understanding Promises

In Praevisio, every compliance requirement becomes a **promise**—a formal, machine-readable commitment that can be automatically verified. Let's look at the promise we'll use in this tutorial. You can find this file already created in your project at `governance/promises/llm-input-logging.yaml`:
```yaml
id: llm-input-logging
version: 0.1.0
domain: /llm/observability
statement: All LLM API calls must log input prompts.
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

Let's break down what each field means, because understanding the promise structure is crucial to using Praevisio effectively.

The **id and version** uniquely identify this promise. As your requirements evolve over time (perhaps you later need to log not just prompts but also model responses), you can create version 0.2.0 without breaking existing code that satisfies 0.1.0. This versioning system lets you update governance requirements gradually across your codebase.

The **domain** places this promise in a hierarchy. The path `/llm/observability` tells Praevisio this is about LLM systems and specifically about observability—the practice of making systems transparent and traceable. In a larger system, you might have dozens of promises across different domains like `/llm/fairness` or `/data/privacy`. Organizing them hierarchically helps you find relevant promises and understand how different governance requirements relate to each other.

The **statement** is where regulatory language becomes precise and testable. Notice we don't say "LLM calls should ideally be logged" or "try to log most LLM calls." We say "must log" and "all calls." This precision is crucial because vague requirements lead to vague compliance. When Praevisio evaluates your code, it's checking against this exact statement.

The **critical flag** tells Praevisio whether this promise is non-negotiable. When set to true, if the promise fails, your commit will be blocked. For less critical promises (like documentation completeness), you might set this to false and accept warnings instead of hard stops. This lets you distinguish between "must have" requirements and "should have" guidelines.

The **success criteria** define what "keeping the promise" means mathematically. The credence threshold of 0.95 means Praevisio needs to be at least 95% confident that your code logs all LLM calls before it will approve the commit. We'll explain credence in detail shortly, but for now, think of it as a probability: given the evidence Praevisio has collected, what's the chance this code actually does what it promises?

The **evidence types** tell Praevisio what kinds of proof to look for. "Procedural" evidence means deterministic tests—things that always give the same answer for the same input, like unit tests that you've already written. "Pattern" evidence means static analysis that looks for patterns in your code without running it. Praevisio will automatically gather both types of evidence and use them together to compute credence.

The **stake field** is for future use when Sponsio's economic accountability layer is fully integrated. For now, you can ignore it or set it to zero. In later tutorials, you'll learn how stakes create economic incentives for accurate governance.

This promise file already exists in your project. You don't need to create it—Praevisio comes with common governance promises pre-configured. You're learning to understand it so you can customize promises for your specific needs later.

## Your Example Application

To demonstrate how Praevisio works, your project includes a simple LLM client in `app/src/llm_client.py`. This is the code we'll be checking for compliance. Let's look at it:
```python
# app/src/llm_client.py

class LLMClient:
    """A minimal LLM client for governance experiments."""
    
    def __init__(self):
        self._logs = []
    
    def generate(self, prompt: str) -> str:
        """Generate a response from the LLM."""
        self._log_prompt(prompt)
        return "This is a placeholder response."
    
    def _log_prompt(self, prompt: str) -> None:
        """Log the input prompt for audit purposes."""
        self._logs.append({"prompt": prompt})
    
    @property
    def logs(self) -> list:
        """Expose captured logs for verification."""
        return self._logs.copy()
```

Notice the critical line in the `generate()` method: `self._log_prompt(prompt)`. This is where logging happens, and this is what our promise requires. In your real application, you'd probably be logging to a database or a proper logging system like the Python logging module. For this tutorial, we're using a simple list so you can see exactly what gets logged.

Your project also includes a test file at `app/tests/test_logging.py` that verifies logging works:
```python
# app/tests/test_logging.py

from app.src.llm_client import LLMClient

def test_prompt_logging():
    """Verify that LLMClient logs every prompt."""
    client = LLMClient()
    response = client.generate("hello")
    assert response == "This is a placeholder response."
    assert client.logs == [{"prompt": "hello"}]
```

This test will serve as procedural evidence when Praevisio evaluates your code. If this test passes, Praevisio knows with certainty that at least the basic logging mechanism works.

## Running Your First Evaluation

Now let's see Praevisio in action. From your project directory, run:
```bash
praevisio evaluate-commit ./
```

Praevisio will analyze your code and produce output like this:
```
Evaluating promise: llm-input-logging
Gathering evidence...
  ✓ Procedural evidence: test_prompt_logging passed
  ✓ Pattern evidence: logging call detected in llm_client.py

Credence: 0.97
Verdict: green
```

Congratulations! Your code keeps its promise. Let's understand what just happened behind the scenes.

## Understanding the Evaluation Process

When you ran `praevisio evaluate-commit`, the system went through several steps:

First, Praevisio loaded the promise definition from `governance/promises/llm-input-logging.yaml`. It now knows what to check for, what evidence types to gather, and what credence threshold is required.

Second, Praevisio gathered procedural evidence by running your test suite. It found and executed `test_prompt_logging()`, which passed. This is strong evidence that logging works—the test actually ran your code and verified that logs were created.

Third, Praevisio gathered pattern evidence using static analysis. It examined your source code and detected that you have a `log()` call in the right place. This is weaker evidence than the test (static analysis doesn't prove the code actually works when run), but it's a useful sanity check.

Fourth, Praevisio combined these evidence types to compute a credence score. Because both the test passed and the pattern check succeeded, credence came out to 0.97—meaning Praevisio is 97% confident your code keeps its promise.

Finally, Praevisio compared credence to the threshold specified in the promise (0.95). Since 0.97 is greater than 0.95, the verdict is green. In a real workflow integrated with git hooks, this would allow your commit to proceed.

## What Is Credence?

Credence is the heart of Praevisio's approach to governance. It's a number between 0 and 1 that represents how confident the system is that your code keeps a specific promise, given the evidence it has collected.

Think of credence as a probability, but not in the frequentist sense of "if I ran this experiment many times, what fraction would succeed?" Instead, it's a Bayesian probability representing the system's degree of belief. It answers the question: "Based on everything I know right now—the tests that passed, the patterns I found, the code structure I analyzed—what's my best estimate of the probability that this code actually does what it promises?"

Why not just pass or fail? Because real-world evidence is messy and uncertain. A single passing test doesn't guarantee your code is perfect—maybe there are edge cases the test didn't cover. Conversely, one failing test doesn't always mean the entire promise is broken—maybe the test itself has a bug. By quantifying confidence with a credence score, Praevisio lets you reason about uncertainty explicitly.

The credence threshold in your promise (0.95) represents your organization's risk tolerance. Setting it to 0.95 means "I need to be at least 95% confident before I'll approve this code." Different organizations might choose different thresholds. A medical device company might require 0.99 for safety-critical promises, while a startup might accept 0.85 for low-risk features. The threshold is your decision—Praevisio just computes the credence honestly.

When both strong evidence (tests) and supporting evidence (static analysis) agree, credence is high (like your 0.97). When evidence conflicts—say, the test passes but static analysis finds no logging call—credence drops because something seems wrong. When all evidence suggests the promise is broken, credence goes very low. This evidence fusion is what makes Praevisio more robust than simple pass/fail checking.

## Seeing a Violation

Now let's see what happens when code violates the promise. Open `app/src/llm_client.py` and temporarily comment out the logging line:
```python
def generate(self, prompt: str) -> str:
    # self._log_prompt(prompt)  # Oops, commented out
    return "This is a placeholder response."
```

Save the file and run the evaluation again:
```bash
praevisio evaluate-commit ./
```

Now you should see output like:
```
Evaluating promise: llm-input-logging
Gathering evidence...
  ✗ Procedural evidence: test_prompt_logging failed
  ✗ Pattern evidence: no logging call detected in llm_client.py

Credence: 0.10
Verdict: red

Issues found:
  - test_prompt_logging failed: expected logs not found
  - static analysis: no log() call detected near generate() method
```

The test failed because no logs were created. The pattern check failed because the logging call is gone. Credence dropped to 0.10 (very low confidence that the promise is kept), and the verdict changed to red. In a real git hook integration, this would block your commit and display these error messages, preventing the broken code from being merged.

This is the core value of Praevisio: immediate, quantitative feedback about whether your code keeps its promises. No waiting for code review, no hoping someone notices the missing logging, no discovering the problem in production six weeks later. The system tells you instantly, with a credence score that reflects the strength of the evidence.

Now restore the logging line (uncomment `self._log_prompt(prompt)`) and verify that the verdict goes back to green. This cycle—make a change, run evaluation, see the verdict—is what Praevisio enables at commit time.

## Understanding the Evidence Pipeline

Praevisio's power comes from gathering multiple types of evidence and combining them intelligently. In this tutorial, you've seen two evidence types:

Procedural evidence (your test) is the strongest. When `test_prompt_logging()` passes, Praevisio knows with certainty that the logging mechanism works for at least one case. Tests are deterministic—they give the same answer every time for the same code. This makes them highly reliable evidence.

Pattern evidence (static analysis) is weaker but still useful. Praevisio's static analyzer examines your code structure and looks for expected patterns—in this case, a call to `log()` near the LLM call. This doesn't prove the code works when run, but it catches obvious violations quickly. If someone deletes the entire logging function, static analysis will notice even before trying to run tests.

By using multiple evidence types, Praevisio becomes more robust. If you only used tests, someone could write a test that always passes but doesn't actually check logging. If you only used static analysis, you might miss subtle bugs where the logging call exists but is unreachable. Using both together provides defense in depth.

In Tutorial 2, you'll learn about more sophisticated evidence types, including real static analysis with Semgrep (replacing the simple pattern matching shown here), code coverage analysis, and git history analysis. Each additional evidence type makes Praevisio's credence calculations more reliable.

## Integrating with Your Workflow

While you've been running `praevisio evaluate-commit` manually in this tutorial, in real use you'll integrate it with your git workflow. Praevisio provides a pre-commit hook that runs automatically when you try to commit code:
```bash
praevisio install-hooks
```

This command sets up git hooks in your repository. Now, every time you run `git commit`, Praevisio will evaluate all relevant promises before allowing the commit to proceed. If any promise fails (credence below threshold), the commit is blocked and you see which promises failed and why.

This creates a safety net that's always active. You can't accidentally commit code that violates governance requirements because Praevisio checks every commit automatically. This is much more reliable than relying on human code reviewers to remember every governance rule.

## What You've Accomplished

Let's review what you've learned in this tutorial:

You understand what a promise is—a formal, machine-readable specification of a compliance requirement. You've seen how promises define not just what should happen, but also how confident the system needs to be before approving code.

You know what credence means—a quantitative measure of confidence that code keeps its promise, computed from evidence. You understand that credence reflects genuine uncertainty and that the threshold lets you control risk tolerance.

You've seen the evidence pipeline in action—how Praevisio gathers procedural evidence from tests and pattern evidence from static analysis, then combines them to compute credence. You understand that different evidence types have different strengths.

You've experienced the core Praevisio workflow: promise → evidence → credence → verdict. This workflow runs automatically at commit time, catching violations before they reach production.

You've seen a violation get caught—when you commented out the logging call, credence dropped and the verdict changed to red. This demonstrated how Praevisio provides immediate feedback that prevents governance failures.

## Why This Approach Works

Traditional governance relies on humans to remember requirements, write code that satisfies them, and catch violations during review. Every step is a potential failure point. A developer might forget about the logging requirement, or a code reviewer might miss that it's missing, especially in a large pull request. The violation only becomes visible weeks later during an audit.

Praevisio removes the human memory burden. The system remembers the requirements (encoded as promises), checks them automatically (by gathering evidence), and quantifies compliance (through credence). Developers don't need to memorize governance rules—the system enforces them.

Moreover, by making credence explicit, you can reason about evidence quality. If credence for a critical promise is barely above the threshold, that's a signal to add more evidence sources or tighten the code. If credence is very high, you can be confident without over-testing. This lets you allocate verification effort efficiently—something manual code review struggles to do.

The quantitative nature of credence also helps when requirements change. If regulators update their logging requirements, you update the promise definition and re-run evaluations. Praevisio immediately tells you which parts of your codebase no longer satisfy the new requirement and need updating. This beats searching through code manually or hoping someone remembers all the places that need changes.

## Next Steps

In Tutorial 2, you'll level up the evidence pipeline by adding real static analysis with Semgrep. You'll learn how to write Semgrep rules that understand Python syntax and catch violations that simple pattern matching would miss. You'll also see how Praevisio weights different evidence types when computing credence, giving more influence to strong evidence and less to weak evidence.

For now, make sure the logging line in `llm_client.py` is uncommented, verify that the verdict is green, and ensure you understand the promise → evidence → credence → verdict flow. That flow is the foundation of everything else in Praevisio.

Try experimenting on your own. What happens if you add more test cases to `test_logging.py`? Does credence change? What if you rename the `_log_prompt()` method to something that doesn't contain the word "log"—does the pattern evidence still work? Playing with the system will deepen your understanding of how evidence affects credence.

You've just completed your first governance check with Praevisio. It's simple, but it's real, and it works. Every subsequent tutorial will build on these same principles, adding more sophisticated evidence sources, more complex promises, and eventually integration with the full ABDUCTIO credence calculation engine. But the core idea—promises that code must provably keep—starts right here.
