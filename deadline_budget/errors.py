"""Exceptions for deadline budget tracking."""


class DeadlineExceededError(Exception):
    """Raised when request deadline budget is exhausted."""

    def __init__(self, budget_seconds: float, elapsed_seconds: float) -> None:
        self.budget_seconds = budget_seconds
        self.elapsed_seconds = elapsed_seconds
        super().__init__(f"Request deadline exceeded: {elapsed_seconds:.2f}s elapsed, budget was {budget_seconds:.2f}s")
