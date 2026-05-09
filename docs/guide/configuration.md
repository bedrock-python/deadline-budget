# Configuration Guide

Advanced configuration options for `deadline-budget`.

## DeadlineBudget Configuration

### Constructor Parameters

```python
from deadline_budget import DeadlineBudget

budget = DeadlineBudget(
    total_seconds=10.0,      # Total budget for orchestration
    min_timeout=0.1,         # Minimum timeout to return
    safety_margin=0.5,       # Reserve time at the end
)
```

#### `total_seconds` (required)

Total time budget for the entire orchestration.

```python
budget = DeadlineBudget(total_seconds=10.0)  # 10 seconds total
```

#### `min_timeout` (optional, default: 0.1)

Minimum timeout value returned by `timeout_for()`. Prevents returning tiny timeouts that are unusable.

```python
budget = DeadlineBudget(total_seconds=10.0, min_timeout=0.1)

# Even if remaining is 0.05s, returns 0.1s
timeout = budget.timeout_for()
```

#### `safety_margin` (optional, default: 0.0)

Reserve time subtracted from total budget to prevent deadline violations:

```python
budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)
# Usable budget: 10.0 - 0.5 = 9.5 seconds
```

**Why use this?** Network latency, processing overhead, or final cleanup operations can cause deadline violations even if individual calls complete within budget. The safety margin ensures you have buffer time.

### Method Parameters

#### `timeout_for(cap=None, min_timeout=None, reserve_for_next=0.0)`

Compute timeout for next downstream call.

```python
# No cap: returns remaining budget (or min_timeout if less)
timeout = budget.timeout_for()

# With cap: returns min(cap, remaining)
timeout = budget.timeout_for(cap=5.0)

# Reserve budget for subsequent calls
timeout = budget.timeout_for(cap=5.0, reserve_for_next=2.0)

# Override instance min_timeout
timeout = budget.timeout_for(min_timeout=0.5)
```

**Parameters:**
- `cap`: Maximum timeout to return (optional)
- `min_timeout`: Override instance min_timeout (optional)
- `reserve_for_next`: Reserve budget for future calls (default: 0.0)

**Returns:** `float` — timeout in seconds

## BudgetContext Configuration

### Creation

```python
from deadline_budget import BudgetContext

ctx = BudgetContext.create(
    total_seconds=10.0,
    call_caps={
        "identity_create_user": 3.0,
        "credential_set_password": 3.0,
        "verification_verify_code": 2.0,
    },
    min_timeout=0.1,
    safety_margin=0.5,
)
```

#### `total_seconds` (required)

Total time budget (same as `DeadlineBudget`).

#### `call_caps` (optional, default: `{}`)

Dictionary mapping call names to maximum timeout caps.

```python
call_caps = {
    "identity_create_user": 3.0,    # Max 3s for this call
    "verification_verify_code": 2.0,  # Max 2s for this call
}

ctx = BudgetContext.create(total_seconds=10.0, call_caps=call_caps)
```

**Behavior:**
- Configured calls: Uses `min(cap, remaining_budget)`
- Unconfigured calls: Uses `remaining_budget`

#### `min_timeout` (optional, default: 0.1)

Minimum timeout (same as `DeadlineBudget`).

#### `safety_margin` (optional, default: 0.0)

Reserve time (same as `DeadlineBudget`).

### Method Parameters

#### `timeout_for_call(call_name, reserve_for_next=0.0)`

Get timeout for a specific call.

```python
# Uses configured cap (if exists)
timeout = ctx.timeout_for_call("identity_create_user")

# Reserve budget for future calls
timeout = ctx.timeout_for_call("identity_create_user", reserve_for_next=2.0)

# Unconfigured call (uses remaining budget)
timeout = ctx.timeout_for_call("some_unconfigured_call")
```

**Parameters:**
- `call_name`: Name of the call (string)
- `reserve_for_next`: Reserve budget for subsequent calls (default: 0.0)

**Returns:** `float` — timeout in seconds

## Choosing Between DeadlineBudget and BudgetContext

### Use `DeadlineBudget` when:

- You need fine-grained control
- Timeout caps vary dynamically
- You want explicit cap specification at each call site

```python
budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)
timeout1 = budget.timeout_for(cap=5.0)
timeout2 = budget.timeout_for(cap=3.0, reserve_for_next=1.0)
```

### Use `BudgetContext` when:

- Timeout caps are known upfront
- You want cleaner, more readable code
- You prefer configuration over inline parameters

```python
ctx = BudgetContext.create(
    total_seconds=10.0,
    call_caps={"method_a": 5.0, "method_b": 3.0},
)
timeout1 = ctx.timeout_for_call("method_a")
timeout2 = ctx.timeout_for_call("method_b")
```

## Best Practices

### 1. Always Set a Safety Margin

```python
# ✅ GOOD: 0.5s safety margin
budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)

# ❌ RISKY: No safety margin
budget = DeadlineBudget(total_seconds=10.0)
```

**Why?** Network latency and processing overhead can cause violations even if calls complete within budget.

### 2. Use Reasonable min_timeout

```python
# ✅ GOOD: 100ms minimum
budget = DeadlineBudget(total_seconds=10.0, min_timeout=0.1)

# ❌ BAD: Too small, unusable
budget = DeadlineBudget(total_seconds=10.0, min_timeout=0.001)
```

**Why?** Tiny timeouts (< 100ms) are often useless due to network roundtrip time.

### 3. Reserve Budget for Cleanup

```python
# Reserve 1s for final cleanup/logging
timeout = budget.timeout_for(cap=5.0, reserve_for_next=1.0)
result = await heavy_operation(timeout=timeout)

# Cleanup has 1s reserved
await cleanup_operation(timeout=budget.timeout_for())
```

### 4. Check Expiration After Critical Sections

```python
await critical_operation(timeout=budget.timeout_for(cap=5.0))
budget.check_expired()  # Fail fast if budget exhausted

await another_operation(timeout=budget.timeout_for(cap=3.0))
```

## Example Configurations

### API Gateway (10s total, 0.5s safety)

```python
ctx = BudgetContext.create(
    total_seconds=10.0,
    safety_margin=0.5,
    min_timeout=0.1,
    call_caps={
        "auth_verify_token": 1.0,
        "service_main_logic": 7.0,
        "logging_record": 0.5,
    },
)
```

### Background Job (60s total, 5s safety)

```python
ctx = BudgetContext.create(
    total_seconds=60.0,
    safety_margin=5.0,
    min_timeout=1.0,
    call_caps={
        "fetch_data": 20.0,
        "process_data": 30.0,
        "store_results": 10.0,
    },
)
```

### Microservice Orchestration (5s total, 0.2s safety)

```python
ctx = BudgetContext.create(
    total_seconds=5.0,
    safety_margin=0.2,
    min_timeout=0.05,
    call_caps={
        "identity_service": 1.5,
        "credential_service": 1.5,
        "notification_service": 1.0,
    },
)
```
