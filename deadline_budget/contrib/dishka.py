"""Dishka provider for request deadline budgeting."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from dishka import Provider, Scope, provide

from ..context import BudgetContext


@runtime_checkable
class OperationDeadlineConfigProtocol(Protocol):
    """Protocol for per-operation deadline configuration."""

    @property
    def budget_timeout(self) -> float:
        """Total budget for this operation in seconds."""
        ...

    @property
    def calls_caps(self) -> dict[str, float]:
        """Per-call timeout caps (key: call_name, value: seconds)."""
        ...

    @property
    def safety_margin(self) -> float | None:
        """Override safety margin for this operation; None = use global default."""
        ...

    @property
    def min_timeout(self) -> float | None:
        """Override minimum per-call timeout for this operation; None = use global default."""
        ...


@runtime_checkable
class DeadlineSettingsProtocol(Protocol):
    """Protocol for request deadline settings."""

    @property
    def default_safety_margin(self) -> float:
        """Default safety margin reserved for finalization in seconds."""
        ...

    @property
    def default_min_timeout(self) -> float:
        """Minimum timeout for any call in seconds."""
        ...

    def config_for_operation(self, operation: str) -> OperationDeadlineConfigProtocol:
        """Get configuration for specific operation."""
        ...


class DeadlineContextFactory:
    """Factory for creating BudgetContext instances from configuration.

    Simplifies use case code by encapsulating configuration lookup and context creation.
    """

    def __init__(self, settings: DeadlineSettingsProtocol) -> None:
        """Initialize factory with deadline settings.

        Args:
            settings: Deadline configuration from application settings.
        """
        self._settings: DeadlineSettingsProtocol = settings

    def create_for_operation(self, operation: Any) -> BudgetContext:
        """Create a BudgetContext configured for the given operation.

        Args:
            operation: The operation name or enum (must have .value or be a string).

        Returns:
            A BudgetContext with operation-specific and per-call configuration.
        """
        op_name = operation.value if hasattr(operation, "value") else str(operation)
        config = self._settings.config_for_operation(op_name)

        safety_margin = (
            config.safety_margin if config.safety_margin is not None else self._settings.default_safety_margin
        )
        min_timeout = config.min_timeout if config.min_timeout is not None else self._settings.default_min_timeout

        return BudgetContext.create(
            total_seconds=config.budget_timeout,
            safety_margin=safety_margin,
            min_timeout=min_timeout,
            call_caps=config.calls_caps,
        )


class DeadlineProvider(Provider):
    """Generic Dishka provider for request deadline budgeting.

    Provides DeadlineContextFactory and optionally per-request BudgetContext.
    """

    scope = Scope.APP

    @provide
    def get_deadline_context_factory(self, settings: DeadlineSettingsProtocol) -> DeadlineContextFactory:
        """Provide deadline context factory."""
        return DeadlineContextFactory(settings)
