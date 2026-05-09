"""Tests for Dishka provider module."""

from enum import Enum

import pytest
from dishka import Scope

from deadline_budget.contrib.dishka import (
    DeadlineContextFactory,
    DeadlineProvider,
    DeadlineSettingsProtocol,
    OperationDeadlineConfigProtocol,
)

pytestmark = pytest.mark.unit


class MockOperationConfig:
    """Mock implementation of OperationDeadlineConfigProtocol."""

    def __init__(
        self,
        budget_timeout: float = 10.0,
        calls_caps: dict[str, float] | None = None,
        safety_margin: float | None = None,
        min_timeout: float | None = None,
    ) -> None:
        self._budget_timeout = budget_timeout
        self._calls_caps = calls_caps or {}
        self._safety_margin = safety_margin
        self._min_timeout = min_timeout

    @property
    def budget_timeout(self) -> float:
        return self._budget_timeout

    @property
    def calls_caps(self) -> dict[str, float]:
        return self._calls_caps

    @property
    def safety_margin(self) -> float | None:
        return self._safety_margin

    @property
    def min_timeout(self) -> float | None:
        return self._min_timeout


class MockSettings:
    """Mock implementation of DeadlineSettingsProtocol."""

    def __init__(
        self,
        default_safety_margin: float = 0.5,
        default_min_timeout: float = 0.1,
        operations: dict[str, OperationDeadlineConfigProtocol] | None = None,
    ) -> None:
        self._default_safety_margin = default_safety_margin
        self._default_min_timeout = default_min_timeout
        self._operations = operations or {}

    @property
    def default_safety_margin(self) -> float:
        return self._default_safety_margin

    @property
    def default_min_timeout(self) -> float:
        return self._default_min_timeout

    def config_for_operation(self, operation: str) -> OperationDeadlineConfigProtocol:
        return self._operations.get(
            operation,
            MockOperationConfig(budget_timeout=10.0),
        )


def test__deadline_context_factory__init__stores_settings() -> None:
    # Arrange
    settings = MockSettings()

    # Act
    factory = DeadlineContextFactory(settings)

    # Assert
    assert factory._settings is settings


def test__factory__create_for_operation_with_string__returns_context_with_config() -> None:
    # Arrange
    settings = MockSettings(
        operations={
            "signup": MockOperationConfig(
                budget_timeout=15.0,
                safety_margin=1.0,
                min_timeout=0.2,
                calls_caps={"identity_create": 3.0},
            ),
        }
    )
    factory = DeadlineContextFactory(settings)

    # Act
    ctx = factory.create_for_operation("signup")

    # Assert
    assert ctx.budget.total_seconds == 14.0  # 15.0 - 1.0 safety
    assert ctx.call_caps == {"identity_create": 3.0}
    timeout = ctx.timeout_for_call("identity_create")
    assert timeout == 3.0


def test__factory__create_for_operation_with_enum__extracts_enum_value() -> None:
    # Arrange
    class Operation(str, Enum):
        SIGNUP = "signup"
        LOGIN = "login"

    settings = MockSettings(
        operations={
            "signup": MockOperationConfig(
                budget_timeout=15.0,
                calls_caps={"identity_create": 3.0},
            ),
        }
    )
    factory = DeadlineContextFactory(settings)

    # Act
    ctx = factory.create_for_operation(Operation.SIGNUP)

    # Assert
    assert ctx.call_caps == {"identity_create": 3.0}


def test__factory__create_with_config_safety_margin__overrides_default_margin() -> None:
    # Arrange
    settings = MockSettings(
        default_safety_margin=0.5,
        operations={
            "critical": MockOperationConfig(
                budget_timeout=10.0,
                safety_margin=2.0,
            ),
        },
    )
    factory = DeadlineContextFactory(settings)

    # Act
    ctx = factory.create_for_operation("critical")

    # Assert
    assert ctx.budget.total_seconds == 8.0


def test__factory__create_with_none_safety_margin__uses_default_margin() -> None:
    # Arrange
    settings = MockSettings(
        default_safety_margin=0.5,
        operations={
            "normal": MockOperationConfig(
                budget_timeout=10.0,
                safety_margin=None,
            ),
        },
    )
    factory = DeadlineContextFactory(settings)

    # Act
    ctx = factory.create_for_operation("normal")

    # Assert
    assert ctx.budget.total_seconds == 9.5


def test__factory__create_with_config_min_timeout__overrides_default_min_timeout() -> None:
    # Arrange
    settings = MockSettings(
        default_safety_margin=0.0,
        default_min_timeout=0.1,
        operations={
            "fast": MockOperationConfig(
                budget_timeout=10.0,
                safety_margin=0.0,
                min_timeout=0.05,
            ),
        },
    )
    factory = DeadlineContextFactory(settings)

    # Act
    ctx = factory.create_for_operation("fast")

    # Assert
    assert ctx.budget.total_seconds == 10.0


def test__factory__create_with_none_min_timeout__uses_default_min_timeout() -> None:
    # Arrange
    settings = MockSettings(
        default_safety_margin=0.0,
        default_min_timeout=0.2,
        operations={
            "normal": MockOperationConfig(
                budget_timeout=10.0,
                safety_margin=0.0,
                min_timeout=None,
            ),
        },
    )
    factory = DeadlineContextFactory(settings)

    # Act
    ctx = factory.create_for_operation("normal")

    # Assert
    assert ctx.budget.total_seconds == 10.0


def test__factory__create_for_unknown_operation__uses_default_config() -> None:
    # Arrange
    settings = MockSettings(
        default_safety_margin=0.5,
        default_min_timeout=0.1,
    )
    factory = DeadlineContextFactory(settings)

    # Act
    ctx = factory.create_for_operation("unknown")

    # Assert
    assert ctx.budget.total_seconds == 9.5
    assert ctx.call_caps == {}


def test__deadline_provider__scope__is_app_scope() -> None:
    # Arrange
    provider = DeadlineProvider()

    # Act
    scope = provider.scope

    # Assert
    assert scope == Scope.APP


def test__protocols__runtime_checkable__validates_mock_implementations() -> None:
    # Arrange
    mock_settings = MockSettings()
    mock_config = MockOperationConfig()

    # Act & Assert
    assert isinstance(mock_settings, DeadlineSettingsProtocol)
    assert isinstance(mock_config, OperationDeadlineConfigProtocol)
