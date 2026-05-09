"""Settings for request deadline budgets."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OperationDeadlineConfig(BaseModel):
    """Deadline configuration for a specific operation."""

    budget_timeout: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description="Total budget for this operation in seconds",
    )
    safety_margin: float | None = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Override global default_safety_margin for this operation; None uses global default",
    )
    min_timeout: float | None = Field(
        default=None,
        ge=0.01,
        le=1.0,
        description="Override global default_min_timeout for this operation; None uses global default",
    )
    calls_caps: dict[str, float] = Field(
        default_factory=dict,
        description="Per-call timeout caps (key: call_name, value: seconds)",
    )


class BaseDeadlineSettings(BaseModel):
    """Base configuration for request deadline budgets."""

    # Per-operation configurations
    operations: dict[str, OperationDeadlineConfig] = Field(
        default_factory=dict,
        description="Per-operation deadline configurations",
    )

    # Global defaults (for operations without specific configuration)
    default_budget_timeout: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description="Default total budget for operations in seconds",
    )
    default_safety_margin: float = Field(
        default=0.5,
        ge=0.0,
        le=5.0,
        description="Safety margin reserved for finalization in seconds",
    )
    default_min_timeout: float = Field(
        default=0.1,
        ge=0.01,
        le=1.0,
        description="Minimum timeout for any call in seconds",
    )

    def config_for_operation(self, operation: str) -> OperationDeadlineConfig:
        """Get configuration for specific operation or return default.

        Args:
            operation: Operation name (e.g., "signup_confirm").

        Returns:
            Configuration for the operation, or default config if not found.
        """
        return self.operations.get(
            operation,
            OperationDeadlineConfig(budget_timeout=self.default_budget_timeout),
        )
