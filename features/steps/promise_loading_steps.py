from pathlib import Path

from behave import given, when, then

from praevisio.infrastructure.promise_loader import YamlPromiseLoader


@given('a promise file "{filename}" exists')
def step_promise_exists(context, filename: str):
    promise_path = Path("governance/promises") / filename
    assert promise_path.exists(), f"Promise file not found: {promise_path}"
    context.promise_path = promise_path


@when('I load promise "{promise_id}"')
def step_load_promise(context, promise_id: str):
    loader = YamlPromiseLoader()
    context.loaded_promise = loader.load(promise_id)


@when('I try to load promise "{promise_id}"')
def step_try_load_promise(context, promise_id: str):
    loader = YamlPromiseLoader()
    try:
        context.loaded_promise = loader.load(promise_id)
        context.error = None
    except Exception as exc:
        context.error = exc


@then('the promise should have id "{expected_id}"')
def step_check_id(context, expected_id: str):
    assert context.loaded_promise.id == expected_id


@then("the promise statement should match the YAML file")
def step_check_statement(context):
    assert context.loaded_promise.statement


@then("a FileNotFoundError should be raised")
def step_check_file_error(context):
    assert isinstance(context.error, FileNotFoundError), f"Got {type(context.error)}"


@then('the error should mention "{text}"')
def step_error_mentions(context, text: str):
    assert text in str(context.error), f"Expected '{text}' in error: {context.error}"
