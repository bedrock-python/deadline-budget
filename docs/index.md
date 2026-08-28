# deadline-budget

Request deadline budget tracking for distributed orchestrations.

## Overview

`deadline-budget` provides a simple way to track request deadline budgets in orchestration flows. Instead of using fixed per-call timeouts that restart on each downstream call, a `DeadlineBudget` maintains a single countdown from the request start, ensuring total request time stays within bounds.

## Features

- **Deadline tracking**: Single countdown timer from orchestration start
- **Per-call caps**: Optional timeout caps for individual downstream calls
- **Safety margins**: Reserve time to prevent deadline violations
- **Simple API**: Low-level `DeadlineBudget` and high-level `BudgetContext`
- **Type-safe**: Full type hints with mypy strict mode
- **Well-tested**: 100% test coverage

## Installation

```bash
pip install deadline-budget
```

**Optional dependencies:**
```bash
pip install deadline-budget[settings]  # Pydantic-based settings
pip install deadline-budget[dishka]    # Dishka DI provider
```

**Requirements:** Python 3.10+

## Quick Examples

### Basic Usage with DeadlineBudget

```python
from deadline_budget import DeadlineBudget

# Initialize budget at orchestrator entry (e.g., 9.5s total with 0.5s safety margin)
budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)

# Each downstream call consumes remaining budget
await identity_service.create_user(..., timeout=budget.timeout_for(cap=5.0))
await credential_service.set_password(..., timeout=budget.timeout_for(cap=5.0))
await verification_service.confirm(..., timeout=budget.timeout_for(cap=5.0))

# Check if expired
if budget.expired():
    raise Exception("Request deadline exceeded")
```

### Convenient Usage with BudgetContext

For cleaner code, use `BudgetContext` to encapsulate per-call timeout caps:

```python
from deadline_budget import BudgetContext

# Define per-call timeout caps
call_caps = {
    "identity_create_user": 3.0,
    "identity_get_user": 2.0,
    "verification_verify_code": 2.0,
    "credential_set_password": 3.0,
}

# Create context with total budget and caps
ctx = BudgetContext.create(
    total_seconds=10.0,
    safety_margin=0.5,
    min_timeout=0.1,
    call_caps=call_caps,
)

# Get timeout for configured call (uses specific cap)
timeout = ctx.timeout_for_call("identity_create_user")
await identity_service.create_user(..., timeout=timeout)

# Get timeout for unconfigured call (uses remaining budget)
timeout = ctx.timeout_for_call("unconfigured_method")
await other_service.some_method(..., timeout=timeout)

# Check expiration and get metrics
ctx.check_expired()
print(f"Consumed: {ctx.elapsed():.2f}s, Remaining: {ctx.remaining():.2f}s")
```

## Why Deadline Budgets?

In distributed orchestrations, using fixed per-call timeouts can lead to total request time exceeding acceptable limits:

```python
# ❌ PROBLEM: Each call restarts timeout, total time = 15s
await service_a.call(..., timeout=5.0)  # Takes 5s
await service_b.call(..., timeout=5.0)  # Takes 5s
await service_c.call(..., timeout=5.0)  # Takes 5s
# Total: 15 seconds!
```

With deadline budgets, the timeout countdown is shared:

```python
# ✅ SOLUTION: Single countdown ensures total ≤ 10s
budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)
await service_a.call(..., timeout=budget.timeout_for(cap=5.0))  # Uses min(5.0, 9.5)
await service_b.call(..., timeout=budget.timeout_for(cap=5.0))  # Uses min(5.0, remaining)
await service_c.call(..., timeout=budget.timeout_for(cap=5.0))  # Uses min(5.0, remaining)
# Total: ≤ 10 seconds guaranteed
```

## Next Steps

- [Quickstart Guide](guide/quickstart.md) — Step-by-step setup and usage
- [API Reference](reference/index.md) — Complete API documentation
- [GitHub Repository](https://github.com/bedrock-python/deadline-budget)
