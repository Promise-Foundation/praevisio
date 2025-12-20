from behave import given, when, then

from app.src.injection_guard import guard


@given("an injection guard module")
def step_guard_module(context):
    context.guard = guard


@when('I guard "{prompt}"')
def step_guard_prompt(context, prompt: str):
    context.guard_result = context.guard(prompt)


@then("the guard should flag it as an attack")
def step_is_attack(context):
    assert context.guard_result["is_attack"] is True, context.guard_result


@then("the guard should not flag it as an attack")
def step_not_attack(context):
    assert context.guard_result["is_attack"] is False, context.guard_result


@then('the reason should mention "{text}"')
def step_reason_mentions(context, text: str):
    reason = context.guard_result["reason"].lower()
    assert text.lower() in reason, f"Expected '{text}' in reason: {reason}"
