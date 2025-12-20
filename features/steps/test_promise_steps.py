from __future__ import annotations

from behave import given, when, then

from praevisio.application.promise_service import PromiseService
from praevisio.infrastructure.repositories import InMemoryPromiseRepository


@given("an in-memory promise repository")
def step_impl_in_memory_repo(context):
    context.repo = InMemoryPromiseRepository()


@given("a promise service")
def step_impl_promise_service(context):
    context.service = PromiseService(context.repo)


@when('I register a promise with id "{promise_id}" and statement "{statement}"')
def step_impl_register_promise(context, promise_id: str, statement: str):
    context.result = context.service.register_promise(promise_id, statement)


@then('the returned promise has id "{expected_id}"')
def step_impl_assert_id(context, expected_id: str):
    assert context.result.id == expected_id


@then('the returned promise has statement "{expected_statement}"')
def step_impl_assert_statement(context, expected_statement: str):
    assert context.result.statement == expected_statement
