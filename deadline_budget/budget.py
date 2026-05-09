"""Core deadline budget implementation."""

from __future__ import annotations

import time

from .errors import DeadlineExceededError


class DeadlineBudget:
    """Tracks request deadline budget using monotonic time.

    Example:
        budget = DeadlineBudget(total_seconds=9.5)
        timeout1 = budget.timeout_for(cap=5.0)
        await some_call(timeout=timeout1)
        timeout2 = budget.timeout_for(cap=5.0)
        await another_call(timeout=timeout2)
        if budget.expired():
            raise DeadlineExceededError(...)
    """

    def __init__(
        self,
        total_seconds: float,
        *,
        min_timeout: float = 0.1,
        safety_margin: float = 0.0,
    ) -> None:
        """Initialize deadline budget.

        Args:
            total_seconds: Total budget for this request in seconds.
            min_timeout: Minimum timeout to return from timeout_for (default 0.1s).
            safety_margin: Safety margin reserved at the end (subtracted from total).
        """
        if total_seconds <= 0:
            raise ValueError("total_seconds must be positive")
        if min_timeout < 0:
            raise ValueError("min_timeout must be non-negative")
        if safety_margin < 0:
            raise ValueError("safety_margin must be non-negative")
        if safety_margin >= total_seconds:
            raise ValueError("safety_margin must be less than total_seconds")

        self._total_seconds = total_seconds - safety_margin
        self._min_timeout = min_timeout
        self._started_at = time.monotonic()

    def remaining(self) -> float:
        """Return remaining time budget in seconds.

        Returns negative value if deadline already exceeded.
        """
        elapsed = time.monotonic() - self._started_at
        return self._total_seconds - elapsed

    def elapsed(self) -> float:
        """Return elapsed time since budget start in seconds."""
        return time.monotonic() - self._started_at

    def expired(self) -> bool:
        """Check if budget is exhausted."""
        return self.remaining() <= 0

    def timeout_for(
        self,
        cap: float | None = None,
        min_timeout: float | None = None,
        reserve_for_next: float = 0.0,
    ) -> float:
        """Compute timeout for the next downstream call.

        Args:
            cap: Maximum allowed timeout for this call (service-level cap).
            min_timeout: Minimum timeout override (default: use budget min_timeout).
            reserve_for_next: Reserve this many seconds for subsequent steps.

        Returns:
            Computed timeout in seconds, bounded by [min_timeout, cap].

        Raises:
            DeadlineExceededError: If remaining budget is already exhausted.
        """
        remaining = self.remaining()
        if remaining <= 0:
            raise DeadlineExceededError(
                budget_seconds=self._total_seconds,
                elapsed_seconds=self.elapsed(),
            )

        effective_min = min_timeout if min_timeout is not None else self._min_timeout
        available = max(remaining - reserve_for_next, effective_min)

        if cap is not None:
            return min(available, cap)
        return available

    def check_expired(self) -> None:
        """Raise DeadlineExceededError if budget is exhausted."""
        if self.expired():
            raise DeadlineExceededError(
                budget_seconds=self._total_seconds,
                elapsed_seconds=self.elapsed(),
            )

    @property
    def total_seconds(self) -> float:
        """Return total budget in seconds."""
        return self._total_seconds
