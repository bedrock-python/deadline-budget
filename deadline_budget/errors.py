"""Exceptions for deadline budget tracking."""


class DeadlineExceededError(Exception):
    """Raised when request deadline budget is exhausted.

    Initialises ``Exception`` directly rather than via ``super()``, so it is safe to use as the first base
    of a class that also inherits from an exception with an incompatible ``__init__`` signature.

    Attributes:
        budget_seconds: Usable budget in seconds (total minus safety margin).
        elapsed_seconds: Time elapsed since the budget started, in seconds.
    """

    def __init__(self, budget_seconds: float, elapsed_seconds: float) -> None:
        self.budget_seconds = budget_seconds
        self.elapsed_seconds = elapsed_seconds
        # Not super(): under multiple inheritance super() follows the instance MRO and would hand this
        # message to a sibling base's __init__ instead of Exception's.
        Exception.__init__(
            self,
            f"Request deadline exceeded: {elapsed_seconds:.2f}s elapsed, budget was {budget_seconds:.2f}s",
        )
