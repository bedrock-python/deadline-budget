"""Unit tests for DeadlineBudget."""

import time

import pytest

from deadline_budget import DeadlineBudget, DeadlineExceededError

pytestmark = pytest.mark.unit


def test__deadline_budget__init_with_valid_total__creates_budget_with_correct_properties() -> None:
    # Arrange
    total_seconds = 10.0

    # Act
    budget = DeadlineBudget(total_seconds=total_seconds)

    # Assert
    assert budget.total_seconds == 10.0
    assert budget.remaining() > 0
    assert not budget.expired()


def test__deadline_budget__init_with_safety_margin__reduces_total_by_margin() -> None:
    # Arrange
    total_seconds = 10.0
    safety_margin = 0.5

    # Act
    budget = DeadlineBudget(total_seconds=total_seconds, safety_margin=safety_margin)

    # Assert
    assert budget.total_seconds == 9.5


def test__deadline_budget__init_with_negative_total__raises_value_error() -> None:
    # Arrange
    invalid_total = -1.0

    # Act & Assert
    with pytest.raises(ValueError, match="total_seconds must be positive"):
        DeadlineBudget(total_seconds=invalid_total)


def test__deadline_budget__init_with_negative_min_timeout__raises_value_error() -> None:
    # Arrange
    invalid_min_timeout = -0.1

    # Act & Assert
    with pytest.raises(ValueError, match="min_timeout must be non-negative"):
        DeadlineBudget(total_seconds=10.0, min_timeout=invalid_min_timeout)


def test__deadline_budget__init_with_negative_safety_margin__raises_value_error() -> None:
    # Arrange
    invalid_safety_margin = -0.5

    # Act & Assert
    with pytest.raises(ValueError, match="safety_margin must be non-negative"):
        DeadlineBudget(total_seconds=10.0, safety_margin=invalid_safety_margin)


def test__deadline_budget__init_with_safety_margin_gte_total__raises_value_error() -> None:
    # Arrange
    total_seconds = 10.0
    invalid_safety_margin = 10.0

    # Act & Assert
    with pytest.raises(ValueError, match="safety_margin must be less than total_seconds"):
        DeadlineBudget(total_seconds=total_seconds, safety_margin=invalid_safety_margin)


def test__deadline_budget__remaining_after_delay__decreases_over_time() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=1.0)
    initial = budget.remaining()

    # Act
    time.sleep(0.05)
    later = budget.remaining()

    # Assert
    assert later < initial


def test__deadline_budget__elapsed_after_delay__increases_over_time() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=1.0)
    initial = budget.elapsed()

    # Act
    time.sleep(0.05)
    later = budget.elapsed()

    # Assert
    assert later > initial
    assert later >= 0.04


def test__deadline_budget__expired_initially__returns_false() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=10.0)

    # Act
    result = budget.expired()

    # Assert
    assert not result


def test__deadline_budget__expired_after_budget_exhausted__returns_true() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=0.05)

    # Act
    time.sleep(0.1)
    result = budget.expired()

    # Assert
    assert result


def test__deadline_budget__timeout_for_with_cap__returns_cap_value() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=10.0)
    cap = 5.0

    # Act
    timeout = budget.timeout_for(cap=cap)

    # Assert
    assert timeout == 5.0


def test__deadline_budget__timeout_for_when_remaining_less_than_cap__returns_remaining() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=0.2)
    cap = 5.0

    # Act
    time.sleep(0.05)
    timeout = budget.timeout_for(cap=cap)

    # Assert
    assert timeout < 5.0
    assert timeout > 0


def test__deadline_budget__timeout_for_with_reserve__reduces_available_time() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=5.0)
    cap = 10.0
    reserve = 1.0

    # Act
    timeout = budget.timeout_for(cap=cap, reserve_for_next=reserve)

    # Assert
    assert timeout <= 4.0


def test__deadline_budget__timeout_for_when_below_min__enforces_min_timeout() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=0.3, min_timeout=0.5)

    # Act
    time.sleep(0.05)
    timeout = budget.timeout_for(cap=10.0)

    # Assert
    assert timeout == 0.5


def test__deadline_budget__timeout_for_when_expired__raises_deadline_exceeded() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=0.05)
    time.sleep(0.1)

    # Act & Assert
    with pytest.raises(DeadlineExceededError):
        budget.timeout_for()


def test__deadline_budget__check_expired_when_expired__raises_with_details() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=0.05)
    time.sleep(0.1)

    # Act & Assert
    with pytest.raises(DeadlineExceededError) as exc_info:
        budget.check_expired()
    assert exc_info.value.budget_seconds == 0.05
    assert exc_info.value.elapsed_seconds >= 0.08


def test__deadline_budget__check_expired_when_not_expired__does_not_raise() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=10.0)

    # Act & Assert
    budget.check_expired()


def test__deadline_budget__multiple_timeout_for_calls__consume_budget() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=1.0)

    # Act
    timeout1 = budget.timeout_for(cap=5.0)
    time.sleep(0.3)
    timeout2 = budget.timeout_for(cap=5.0)

    # Assert
    assert timeout2 < timeout1


def test__deadline_budget__timeout_for_without_cap__returns_remaining_time() -> None:
    # Arrange
    budget = DeadlineBudget(total_seconds=3.0)

    # Act
    timeout = budget.timeout_for()

    # Assert
    assert abs(timeout - 3.0) < 0.1
