"""Tests for BudgetContext."""

import time

import pytest

from deadline_budget import BudgetContext, DeadlineExceededError

pytestmark = pytest.mark.unit


def test__budget_context__create_with_call_caps__creates_context_with_caps() -> None:
    # Arrange
    call_caps = {
        "identity_create_user": 5.0,
        "verification_verify_code": 4.0,
        "credential_set_password": 3.0,
    }

    # Act
    ctx = BudgetContext.create(total_seconds=10.0, call_caps=call_caps)

    # Assert
    assert ctx.remaining() > 0
    assert ctx.elapsed() >= 0
    assert not ctx.expired()
    assert ctx.call_caps == call_caps


def test__budget_context__create_without_caps__creates_context_with_empty_caps() -> None:
    # Arrange & Act
    ctx = BudgetContext.create(total_seconds=10.0)

    # Assert
    assert ctx.remaining() > 0
    assert ctx.call_caps == {}


def test__budget_context__timeout_for_call_with_cap__applies_call_specific_cap() -> None:
    # Arrange
    call_caps = {
        "identity_create_user": 5.0,
        "verification_verify_code": 2.0,
    }
    ctx = BudgetContext.create(total_seconds=10.0, call_caps=call_caps)

    # Act
    timeout_identity = ctx.timeout_for_call("identity_create_user")
    timeout_verification = ctx.timeout_for_call("verification_verify_code")

    # Assert
    assert timeout_identity == 5.0
    assert timeout_verification == 2.0


def test__budget_context__timeout_for_call_without_cap__uses_remaining_budget() -> None:
    # Arrange
    call_caps = {"identity_create_user": 5.0}
    ctx = BudgetContext.create(total_seconds=3.0, call_caps=call_caps)

    # Act
    timeout = ctx.timeout_for_call("unconfigured_call")

    # Assert
    assert 2.5 < timeout < 3.5


def test__budget_context__timeout_for_call_when_remaining_less_than_cap__returns_remaining() -> None:
    # Arrange
    call_caps = {"slow_call": 10.0}
    ctx = BudgetContext.create(total_seconds=3.0, call_caps=call_caps)

    # Act
    time.sleep(2.0)
    timeout = ctx.timeout_for_call("slow_call")

    # Assert
    assert 0.5 < timeout < 1.5


def test__budget_context__timeout_for_call_with_reserve__reduces_available_time() -> None:
    # Arrange
    call_caps = {"identity_create_user": 10.0}
    ctx = BudgetContext.create(total_seconds=5.0, call_caps=call_caps, min_timeout=0.1)

    # Act
    timeout = ctx.timeout_for_call("identity_create_user", reserve_for_next=2.0)

    # Assert
    assert 2.5 < timeout < 3.5


def test__budget_context__check_expired_when_budget_exhausted__raises_with_details() -> None:
    # Arrange
    ctx = BudgetContext.create(total_seconds=0.5, call_caps={})
    time.sleep(0.6)

    # Act & Assert
    with pytest.raises(DeadlineExceededError) as exc_info:
        ctx.check_expired()
    assert exc_info.value.budget_seconds == 0.5
    assert exc_info.value.elapsed_seconds > 0.5


def test__budget_context__timeout_for_call_when_expired__raises_deadline_exceeded() -> None:
    # Arrange
    call_caps = {"identity_create_user": 5.0}
    ctx = BudgetContext.create(total_seconds=0.5, call_caps=call_caps)
    time.sleep(0.6)

    # Act & Assert
    with pytest.raises(DeadlineExceededError):
        ctx.timeout_for_call("identity_create_user")


def test__budget_context__expired_after_budget_exhausted__returns_true() -> None:
    # Arrange
    ctx = BudgetContext.create(total_seconds=0.5, call_caps={})

    # Act
    initial_expired = ctx.expired()
    time.sleep(0.6)
    final_expired = ctx.expired()

    # Assert
    assert not initial_expired
    assert final_expired


def test__budget_context__create_with_safety_margin__reserves_time_from_budget() -> None:
    # Arrange
    call_caps = {"identity_create_user": 10.0}

    # Act
    ctx = BudgetContext.create(
        total_seconds=5.0,
        safety_margin=1.0,
        call_caps=call_caps,
    )

    # Assert
    initial_remaining = ctx.remaining()
    assert 3.9 < initial_remaining < 4.1


def test__budget_context__access_underlying_budget__allows_direct_budget_operations() -> None:
    # Arrange
    call_caps = {"identity_create_user": 5.0}
    ctx = BudgetContext.create(total_seconds=10.0, call_caps=call_caps)

    # Act
    budget_total = ctx.budget.total_seconds
    timeout = ctx.budget.timeout_for(cap=3.0)

    # Assert
    assert budget_total == 10.0
    assert timeout == 3.0
