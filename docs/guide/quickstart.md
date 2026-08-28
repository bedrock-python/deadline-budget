# Quickstart Guide

This guide shows how to use `deadline-budget` in your orchestration code.

## Installation

```bash
pip install deadline-budget
```

## Basic Concepts

### The Problem

In distributed orchestrations, fixed per-call timeouts don't protect against total request time:

```python
# Each call has 5s timeout, but total = 15s
await service_a.call(timeout=5.0)
await service_b.call(timeout=5.0)
await service_c.call(timeout=5.0)
```

### The Solution

A deadline budget maintains a single countdown from request start:

```python
from deadline_budget import DeadlineBudget

budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)
await service_a.call(timeout=budget.timeout_for(cap=5.0))
await service_b.call(timeout=budget.timeout_for(cap=5.0))
await service_c.call(timeout=budget.timeout_for(cap=5.0))
# Total time guaranteed ≤ 10s
```

## Option 1: Low-Level API (`DeadlineBudget`)

For fine-grained control, use `DeadlineBudget` directly:

```python
from deadline_budget import DeadlineBudget, DeadlineExceededError

# Create budget (10s total, 0.5s safety margin = 9.5s usable)
budget = DeadlineBudget(
    total_seconds=10.0,
    safety_margin=0.5,
    min_timeout=0.1,
)

# Get timeout for each downstream call
timeout1 = budget.timeout_for(cap=5.0)  # Returns min(5.0, remaining)
result1 = await identity_service.create_user(email="...", timeout=timeout1)

timeout2 = budget.timeout_for(cap=3.0)
result2 = await credential_service.set_password(user_id=..., timeout=timeout2)

# Check if budget exhausted
if budget.expired():
    raise DeadlineExceededError(budget_seconds=budget.total_seconds, elapsed_seconds=budget.elapsed())

# Or raise exception if expired
budget.check_expired()

# Get metrics
print(f"Elapsed: {budget.elapsed():.2f}s")
print(f"Remaining: {budget.remaining():.2f}s")
```

## Option 2: High-Level API (`BudgetContext`)

For cleaner code with per-call timeout caps, use `BudgetContext`:

```python
from deadline_budget import BudgetContext

# Define per-call timeout caps
call_caps = {
    "identity_create_user": 3.0,
    "identity_get_user": 2.0,
    "credential_set_password": 3.0,
    "verification_verify_code": 2.0,
}

# Create context
ctx = BudgetContext.create(
    total_seconds=10.0,
    safety_margin=0.5,
    min_timeout=0.1,
    call_caps=call_caps,
)

# Get timeout for configured calls (uses cap)
timeout = ctx.timeout_for_call("identity_create_user")
result1 = await identity_service.create_user(email="...", timeout=timeout)

# Get timeout for unconfigured calls (uses remaining budget)
timeout = ctx.timeout_for_call("some_other_call")
result2 = await other_service.method(..., timeout=timeout)

# Check expiration
ctx.check_expired()

# Access metrics
print(f"Consumed: {ctx.elapsed():.2f}s")
print(f"Remaining: {ctx.remaining():.2f}s")
```

## Parameters Explained

### `total_seconds`

Total time budget for the entire orchestration.

```python
budget = DeadlineBudget(total_seconds=10.0)  # 10 seconds total
```

### `safety_margin`

Reserve time subtracted from total budget to prevent last-moment deadline violations:

```python
# 10s total - 0.5s safety = 9.5s usable
budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)
```

**Why use this?** Prevents returning timeouts that expire during network roundtrip.

### `min_timeout`

Minimum timeout value returned by `timeout_for()`:

```python
budget = DeadlineBudget(total_seconds=10.0, min_timeout=0.1)
# Even if remaining is 0.05s, returns 0.1s
```

**Default:** 0.1 seconds

### `cap`

Maximum timeout for a specific call:

```python
# If remaining is 8s, returns 5s (capped)
timeout = budget.timeout_for(cap=5.0)

# If remaining is 3s, returns 3s (under cap)
timeout = budget.timeout_for(cap=5.0)
```

### `reserve_for_next`

Reserve budget for subsequent calls:

```python
# Reserve 2s for final call
timeout = budget.timeout_for(cap=5.0, reserve_for_next=2.0)
# If remaining is 7s, returns min(5.0, 7.0 - 2.0) = 5s
```

## Example: User Registration Flow

```python
from deadline_budget import BudgetContext, DeadlineExceededError

async def register_user(email: str, password: str) -> User:
    # Define per-service timeout caps
    call_caps = {
        "identity_create_user": 3.0,
        "credential_set_password": 3.0,
        "verification_send_code": 2.0,
    }

    # Create budget context
    ctx = BudgetContext.create(
        total_seconds=10.0,
        safety_margin=0.5,
        min_timeout=0.1,
        call_caps=call_caps,
    )

    try:
        # Step 1: Create user (max 3s)
        user = await identity_service.create_user(
            email=email,
            timeout=ctx.timeout_for_call("identity_create_user"),
        )

        # Step 2: Set password (max 3s)
        await credential_service.set_password(
            user_id=user.id,
            password=password,
            timeout=ctx.timeout_for_call("credential_set_password"),
        )

        # Step 3: Send verification (max 2s)
        await verification_service.send_code(
            user_id=user.id,
            timeout=ctx.timeout_for_call("verification_send_code"),
        )

        # Check final budget
        ctx.check_expired()

        return user

    except DeadlineExceededError:
        # Handle deadline violation
        logger.error(f"Registration exceeded deadline: {ctx.elapsed():.2f}s")
        raise
```

## Next Steps

- [Configuration Guide](configuration.md) — Advanced configuration options
- [API Reference](../reference/index.md) — Complete API documentation
