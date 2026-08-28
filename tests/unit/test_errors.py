"""Unit tests for DeadlineExceededError."""

import pytest

from deadline_budget import DeadlineExceededError

pytestmark = pytest.mark.unit


class StructuredError:
    """Payload of a domain error: an object, not a message string."""

    def __init__(self, code: str, status: int) -> None:
        self.code = code
        self.status = status


class DomainError(Exception):
    """Sibling base whose __init__ rejects anything that is not a StructuredError."""

    def __init__(self, error: StructuredError, *, is_public: bool = False) -> None:
        if not isinstance(error, StructuredError):
            raise TypeError(f"DomainError expects a StructuredError, got {type(error).__name__}")
        self.error = error
        self.is_public = is_public
        super().__init__(error.code)


class RequestDeadlineExceededError(DeadlineExceededError, DomainError):
    """Downstream error that is both a DeadlineExceededError and a DomainError."""

    def __init__(self, budget_seconds: float, elapsed_seconds: float) -> None:
        DeadlineExceededError.__init__(self, budget_seconds, elapsed_seconds)
        DomainError.__init__(self, StructuredError("REQUEST_DEADLINE_EXCEEDED", 504), is_public=True)


def test__deadline_exceeded_error__init__stores_attributes_and_formats_message() -> None:
    # Arrange
    budget_seconds = 10.0
    elapsed_seconds = 12.5

    # Act
    exc = DeadlineExceededError(budget_seconds=budget_seconds, elapsed_seconds=elapsed_seconds)

    # Assert
    assert exc.budget_seconds == 10.0
    assert exc.elapsed_seconds == 12.5
    assert str(exc) == "Request deadline exceeded: 12.50s elapsed, budget was 10.00s"
    assert exc.args == ("Request deadline exceeded: 12.50s elapsed, budget was 10.00s",)


def test__deadline_exceeded_error__as_first_base_with_incompatible_sibling__constructs_cleanly() -> None:
    # Arrange & Act
    exc = RequestDeadlineExceededError(budget_seconds=10.0, elapsed_seconds=12.5)

    # Assert
    assert exc.budget_seconds == 10.0
    assert exc.elapsed_seconds == 12.5
    assert exc.error.code == "REQUEST_DEADLINE_EXCEEDED"
    assert exc.error.status == 504
    assert exc.is_public is True


def test__deadline_exceeded_error__multiply_inherited_subclass__is_caught_by_except_deadline_exceeded() -> None:
    # Arrange
    def orchestrate() -> None:
        raise RequestDeadlineExceededError(budget_seconds=10.0, elapsed_seconds=12.5)

    # Act & Assert
    with pytest.raises(DeadlineExceededError) as exc_info:
        orchestrate()
    assert isinstance(exc_info.value, DomainError)
    assert exc_info.value.budget_seconds == 10.0
    assert exc_info.value.elapsed_seconds == 12.5


def test__deadline_exceeded_error__subclass_calling_super_init__keeps_message() -> None:
    # Arrange
    class CustomDeadlineError(DeadlineExceededError):
        def __init__(self, budget_seconds: float, elapsed_seconds: float) -> None:
            super().__init__(budget_seconds, elapsed_seconds)

    # Act
    exc = CustomDeadlineError(budget_seconds=10.0, elapsed_seconds=12.5)

    # Assert
    assert str(exc) == "Request deadline exceeded: 12.50s elapsed, budget was 10.00s"
    assert exc.budget_seconds == 10.0
    assert exc.elapsed_seconds == 12.5
