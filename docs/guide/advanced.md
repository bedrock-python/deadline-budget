# Advanced Usage

Advanced patterns and techniques for `deadline-budget`.

## Dynamic Timeout Caps

Calculate timeout caps based on runtime conditions:

```python
from deadline_budget import DeadlineBudget

def get_timeout_cap(operation: str, priority: str) -> float:
    """Get timeout cap based on operation and priority."""
    caps = {
        ("create_user", "high"): 5.0,
        ("create_user", "low"): 2.0,
        ("send_email", "high"): 3.0,
        ("send_email", "low"): 1.0,
    }
    return caps.get((operation, priority), 1.0)

budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)

# Dynamic cap based on priority
timeout = budget.timeout_for(cap=get_timeout_cap("create_user", priority="high"))
await identity_service.create_user(email="...", timeout=timeout)
```

## Nested Orchestrations

Pass budgets to nested orchestrations:

```python
from deadline_budget import BudgetContext

async def register_user(ctx: BudgetContext, email: str, password: str) -> User:
    """Nested orchestration that receives parent budget."""
    user = await identity_service.create_user(
        email=email,
        timeout=ctx.timeout_for_call("identity_create_user"),
    )

    await credential_service.set_password(
        user_id=user.id,
        password=password,
        timeout=ctx.timeout_for_call("credential_set_password"),
    )

    return user

async def register_and_notify(email: str, password: str) -> User:
    """Parent orchestration."""
    ctx = BudgetContext.create(
        total_seconds=15.0,
        safety_margin=0.5,
        call_caps={
            "identity_create_user": 3.0,
            "credential_set_password": 3.0,
            "notification_send": 2.0,
        },
    )

    # Pass budget to nested orchestration
    user = await register_user(ctx, email, password)

    # Continue using same budget
    await notification_service.send_welcome(
        user_id=user.id,
        timeout=ctx.timeout_for_call("notification_send"),
    )

    return user
```

## Progressive Timeout Caps

Reduce timeout caps as budget depletes:

```python
from deadline_budget import DeadlineBudget

budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)

# Early calls: generous caps
timeout1 = budget.timeout_for(cap=5.0)
await service_a.call(timeout=timeout1)

# Later calls: tighter caps
timeout2 = budget.timeout_for(cap=3.0)
await service_b.call(timeout=timeout2)

# Final calls: minimal caps
timeout3 = budget.timeout_for(cap=1.0)
await service_c.call(timeout=timeout3)
```

## Conditional Logic Based on Remaining Budget

```python
from deadline_budget import BudgetContext

ctx = BudgetContext.create(total_seconds=10.0, safety_margin=0.5)

# Step 1: Always execute
user = await identity_service.create_user(
    email="...",
    timeout=ctx.timeout_for_call("identity_create_user"),
)

# Step 2: Only if sufficient budget remains
if ctx.remaining() > 2.0:
    await analytics_service.track_signup(
        user_id=user.id,
        timeout=ctx.timeout_for_call("analytics_track"),
    )
else:
    logger.warning("Skipping analytics due to insufficient budget")
```

## Metrics Collection

Track budget consumption for monitoring:

```python
from deadline_budget import BudgetContext, DeadlineExceededError
import time

async def instrumented_orchestration():
    ctx = BudgetContext.create(total_seconds=10.0, safety_margin=0.5)

    start = time.perf_counter()

    try:
        await step_1(ctx)
        await step_2(ctx)
        await step_3(ctx)

        # Collect metrics
        elapsed = ctx.elapsed()
        remaining = ctx.remaining()
        utilization = (elapsed / 10.0) * 100

        metrics.record({
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "budget_utilization_percent": utilization,
        })

    except DeadlineExceededError as e:
        metrics.increment("deadline_exceeded")
        raise
```

## Custom Budget Strategies

Create custom budget allocation strategies:

```python
from deadline_budget import DeadlineBudget

class AdaptiveBudget:
    """Budget that adjusts caps based on historical performance."""

    def __init__(self, total_seconds: float, call_history: dict[str, float]):
        self.budget = DeadlineBudget(total_seconds=total_seconds, safety_margin=0.5)
        self.call_history = call_history  # Historical avg duration per call

    def timeout_for_call(self, call_name: str) -> float:
        """Use historical avg + 50% buffer as cap."""
        avg_duration = self.call_history.get(call_name, 1.0)
        cap = avg_duration * 1.5
        return self.budget.timeout_for(cap=cap)

# Usage
history = {
    "identity_create_user": 1.8,  # Historical avg: 1.8s
    "credential_set_password": 1.2,
}

adaptive = AdaptiveBudget(total_seconds=10.0, call_history=history)
timeout = adaptive.timeout_for_call("identity_create_user")  # cap = 1.8 * 1.5 = 2.7s
```

## Error Recovery with Budget

Retry with reduced timeouts on failure:

```python
from deadline_budget import DeadlineBudget
import asyncio

async def call_with_retry(
    budget: DeadlineBudget,
    func,
    max_retries: int = 2,
    cap: float = 5.0,
):
    """Retry with progressively smaller timeouts."""
    for attempt in range(max_retries + 1):
        budget.check_expired()

        # Reduce cap on retries
        retry_cap = cap / (attempt + 1)
        timeout = budget.timeout_for(cap=retry_cap)

        try:
            return await func(timeout=timeout)
        except asyncio.TimeoutError:
            if attempt == max_retries:
                raise
            continue

# Usage
budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)
result = await call_with_retry(
    budget,
    lambda timeout: identity_service.create_user(email="...", timeout=timeout),
    max_retries=2,
    cap=5.0,
)
```

## Composing `DeadlineExceededError` into Your Error Hierarchy

Services with their own error taxonomy often want one error that is *both* a `DeadlineExceededError` — so
`except DeadlineExceededError` keeps catching it — and a domain error the transport layer already knows how to
map (for example to HTTP 504). `DeadlineExceededError` initialises `Exception` directly rather than through
`super()`, so it can be listed alongside a base whose `__init__` takes something other than a message string:

```python
from deadline_budget import BudgetContext, DeadlineExceededError

class DomainError(Exception):
    """Application error carrying a structured payload instead of a message string."""

    def __init__(self, error: Error, *, is_public: bool = False) -> None:
        self.error = error
        self.is_public = is_public
        super().__init__(error.code)

class RequestDeadlineExceededError(DeadlineExceededError, DomainError):
    def __init__(self, budget_seconds: float, elapsed_seconds: float) -> None:
        DeadlineExceededError.__init__(self, budget_seconds, elapsed_seconds)
        DomainError.__init__(self, Error("REQUEST_DEADLINE_EXCEEDED", 504), is_public=True)

async def register_user(ctx: BudgetContext, email: str) -> User:
    try:
        return await identity_service.create_user(
            email=email,
            timeout=ctx.timeout_for_call("identity_create_user"),
        )
    except DeadlineExceededError as exc:
        raise RequestDeadlineExceededError(exc.budget_seconds, exc.elapsed_seconds) from exc
```

Two rules keep this working:

1. **List `DeadlineExceededError` first.** A base that calls `super().__init__()` hands its arguments to whatever
   comes next in the MRO; placed before `DeadlineExceededError`, the `DomainError` above would pass `error.code`
   into `DeadlineExceededError.__init__`.
2. **Call each base's `__init__` explicitly.** The two bases take different arguments, so a single
   `super().__init__()` chain cannot serve both.

Whichever base initialises `Exception` last sets `exc.args` and therefore `str(exc)`; `budget_seconds` and
`elapsed_seconds` are set on the instance regardless of order.

## Integration with Observability

Integrate with OpenTelemetry or other tracing:

```python
from deadline_budget import BudgetContext
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def traced_orchestration():
    ctx = BudgetContext.create(total_seconds=10.0, safety_margin=0.5)

    with tracer.start_as_current_span("orchestration") as span:
        span.set_attribute("budget.total", 10.0)
        span.set_attribute("budget.safety_margin", 0.5)

        await step_1(ctx)
        span.set_attribute("budget.after_step_1", ctx.remaining())

        await step_2(ctx)
        span.set_attribute("budget.after_step_2", ctx.remaining())

        span.set_attribute("budget.final_elapsed", ctx.elapsed())
        span.set_attribute("budget.final_remaining", ctx.remaining())
```

## Testing with Budgets

Mock `time.monotonic` — the clock `DeadlineBudget` reads — for deterministic tests:

```python
from unittest.mock import patch
from deadline_budget import DeadlineBudget

def test_budget_exhaustion():
    with patch("time.monotonic") as mock_time:
        mock_time.return_value = 0.0
        budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)

        # Simulate 5s elapsed
        mock_time.return_value = 5.0
        assert budget.remaining() == 4.5  # 10 - 0.5 safety - 5 elapsed

        # Simulate 10s elapsed (budget exhausted)
        mock_time.return_value = 10.0
        assert budget.expired()
```

## Best Practices

1. **Always set safety margins** — Network latency and overhead can cause violations
2. **Monitor budget utilization** — Track metrics to tune caps
3. **Fail fast** — Check expiration after critical sections
4. **Reserve for cleanup** — Use `reserve_for_next` for final operations
5. **Pass budgets down** — Share budgets with nested orchestrations
6. **Log budget state** — Include elapsed/remaining in error logs
