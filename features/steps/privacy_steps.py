from behave import given, when, then

from app.src.privacy import redact


@given("a privacy redaction module")
def step_privacy_module(context):
    context.redactor = redact


@when('I redact "{text}"')
def step_redact_text(context, text: str):
    context.redacted = context.redactor(text)


@then('the output should not contain "{text}"')
def step_not_contain(context, text: str):
    assert text not in context.redacted, f"Found {text} in {context.redacted}"


@then('the output should contain "{text}"')
def step_contain(context, text: str):
    assert text in context.redacted, f"Missing {text} in {context.redacted}"


@then("the output should contain {count:d} redaction markers")
def step_count_markers(context, count: int):
    markers = context.redacted.count("[REDACTED_")
    assert markers == count, f"Expected {count} markers, found {markers}"
