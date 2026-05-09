"""High-level context wrapper for deadline budgets with per-call timeout caps."""

from __future__ import annotations

from .budget import DeadlineBudget


class BudgetContext:
    """Convenient wrapper around DeadlineBudget with per-call timeout caps.

    Encapsulates deadline budget and per-call timeout configuration for cleaner orchestration code.

    Example:
        # Define caps for each specific call in the operation
        call_caps = {
            "identity_create_user": 3.0,
            "verification_verify_code": 2.0,
            "credential_set_password": 3.0,
        }
        ctx = BudgetContext.create(total_seconds=10.0, call_caps=call_caps)

        # Get timeout for specific call (with configured cap)
        timeout = ctx.timeout_for_call("identity_create_user")
        await identity_client.create_user(timeout=timeout)

        # Get timeout for unconfigured call (uses remaining budget)
        timeout = ctx.timeout_for_call("identity_get_user")
        await identity_client.get_user(timeout=timeout)
    """

    def __init__(self, budget: DeadlineBudget, call_caps: dict[str, float]) -> None:
        """Initialize context with a budget and per-call caps.

        Args:
            budget: The underlying DeadlineBudget instance.
            call_caps: Mapping of call names to their timeout caps in seconds.
                If a call is not in this dict, it will use remaining budget without cap.
        """
        self._budget: DeadlineBudget = budget
        self._call_caps: dict[str, float] = call_caps

    @classmethod
    def create(
        cls,
        total_seconds: float,
        call_caps: dict[str, float] | None = None,
        *,
        min_timeout: float = 0.1,
        safety_margin: float = 0.0,
    ) -> BudgetContext:
        """Create a new budget context with the given parameters.

        Args:
            total_seconds: Total budget for this request in seconds.
            call_caps: Mapping of call names to their timeout caps (optional).
            min_timeout: Minimum timeout to return (default 0.1s).
            safety_margin: Safety margin reserved at the end (default 0.0s).

        Returns:
            A new BudgetContext instance.
        """
        budget = DeadlineBudget(
            total_seconds=total_seconds,
            min_timeout=min_timeout,
            safety_margin=safety_margin,
        )
        return cls(budget=budget, call_caps=call_caps or {})

    def timeout_for_call(self, call_name: str, reserve_for_next: float = 0.0) -> float:
        """Compute timeout for the next downstream call.

        If call_name has a configured cap, applies it. Otherwise uses remaining budget.

        Args:
            call_name: Name of the call (e.g., "identity_create_user", "verification_verify_code").
            reserve_for_next: Reserve this many seconds for subsequent steps.

        Returns:
            Computed timeout in seconds, bounded by [min_timeout, call_cap] if cap exists,
            or [min_timeout, remaining] if no cap configured.

        Raises:
            DeadlineExceededError: If remaining budget is already exhausted.
        """
        cap = self._call_caps.get(call_name)
        return self._budget.timeout_for(cap=cap, reserve_for_next=reserve_for_next)

    def check_expired(self) -> None:
        """Raise DeadlineExceededError if budget is exhausted.

        Raises:
            DeadlineExceededError: If the deadline has passed.
        """
        self._budget.check_expired()

    def remaining(self) -> float:
        """Return remaining time budget in seconds.

        Returns negative value if deadline already exceeded.
        """
        return self._budget.remaining()

    def elapsed(self) -> float:
        """Return elapsed time since budget start in seconds."""
        return self._budget.elapsed()

    def expired(self) -> bool:
        """Check if budget is exhausted."""
        return self._budget.expired()

    @property
    def budget(self) -> DeadlineBudget:
        """Access to underlying budget for advanced use cases."""
        return self._budget

    @property
    def call_caps(self) -> dict[str, float]:
        """Access to configured call caps."""
        return self._call_caps
