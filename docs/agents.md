# deadline-budget for AI agents

> One page holding everything a coding assistant needs to use deadline-budget correctly,
> plus a map of where the rest of the documentation keeps the details it leaves out. Give
> an agent this page rather than the whole site.

| | |
|---|---|
| Package | `deadline-budget` on PyPI, import root `deadline_budget` |
| Requires | Python 3.10+, no runtime dependencies |
| Install | `pip install deadline-budget` · extras: `settings` (Pydantic models), `dishka` (a DI provider) |
| Entry points | `DeadlineBudget`, `BudgetContext` — both from `deadline_budget` |
| Async | None. Every method is synchronous and returns immediately; it reads a clock, it never sleeps, awaits or cancels |
| Source | <https://github.com/bedrock-python/deadline-budget> |

## How to read this page

Every page of this site is also served as raw Markdown at its own URL with `.md` in place
of the trailing slash — this page is `/agents.md`, the configuration guide is
`/guide/configuration.md` — so anything the map below points at can be fetched as plain
text rather than scraped out of HTML. The **Copy page** control at the top of a page does
the same thing for a human with a chat window open. The one exception is the API
reference: its Markdown is a two-line instruction to a docstring renderer rather than the
API, so it carries neither the control nor a `.md` twin — read it as HTML, or read the
docstrings in the source.

Top to bottom before writing code.
[Rules that hold or break the code](#rules-that-hold-or-break-the-code) is the section
correctness lives in. Every name used below is in the public API; if you need something
not listed here, fetch the page the [documentation map](#documentation-map) points at
rather than guessing a method that sounds plausible.

## Scope

**It does** arithmetic on one countdown. You give it a total at the start of a request; it
tells you, at each downstream call, how many seconds that call may have — bounded by a
per-call cap, a floor, and whatever you want to reserve for the steps after it. It tells
you how much is left, how much is gone, and whether the deadline has passed.

**It does not** enforce anything. It starts no timer, spawns no task, cancels nothing,
and wraps no client. It has no transport of its own: no header, no context variable, no
thread-local, no serialisation format. It does not retry, does not sleep, does not know
what a downstream call is, and never converts a client library's timeout error into its
own. Everything it produces is a `float` you have to pass somewhere yourself.

## Mental model

Two nouns and one number.

* **`DeadlineBudget`** — a start instant and a length. Constructed once at the top of a
  request. `total_seconds` minus `safety_margin` is the usable budget; the clock is
  `time.monotonic()` and it starts in `__init__`, not at the first call.
* **`BudgetContext`** — a `DeadlineBudget` plus a `dict[str, float]` of per-call ceilings,
  so call sites name a call instead of repeating a number. It delegates every question to
  the budget it holds.
* **the timeout** — what `timeout_for()` / `timeout_for_call()` return. This is the only
  thing that ever leaves the library, and the only thing that should cross a process
  boundary.

The whole of `timeout_for` is this, and reading it settles most questions:

```python
remaining = (total_seconds - safety_margin) - (time.monotonic() - started_at)
if remaining <= 0:
    raise DeadlineExceededError(budget_seconds=..., elapsed_seconds=...)
available = max(remaining - reserve_for_next, min_timeout)   # the floor wins over the budget
return min(available, cap) if cap is not None else available  # the cap wins over the floor
```

Nothing in that is stateful. Calling `timeout_for()` twice in a row without doing any work
returns the same number twice: the budget is spent by the clock, not by asking.

## Wiring

```python
from deadline_budget import BudgetContext, DeadlineExceededError

async def register_user(email: str, password: str) -> User:
    ctx = BudgetContext.create(
        total_seconds=10.0,     # the whole orchestration
        safety_margin=0.5,      # 9.5s usable; 0.5s left to build a response
        min_timeout=0.1,
        call_caps={             # per-call ceilings, by name
            "identity.create_user": 3.0,
            "credential.set_password": 3.0,
            "verification.send_code": 2.0,
        },
    )

    user = await identity.create_user(
        email, timeout=ctx.timeout_for_call("identity.create_user")
    )
    await credential.set_password(
        user.id, password, timeout=ctx.timeout_for_call("credential.set_password")
    )

    ctx.check_expired()         # fail here rather than start work that cannot finish
    await verification.send_code(
        user.id, timeout=ctx.timeout_for_call("verification.send_code")
    )
    return user
```

`DeadlineBudget` is the same flow with the cap written at each call site:
`budget.timeout_for(cap=3.0)`.

## The API

### `DeadlineBudget`

`DeadlineBudget(total_seconds, *, min_timeout=0.1, safety_margin=0.0)` — `min_timeout` and
`safety_margin` are keyword-only. `ValueError` if `total_seconds <= 0`, if `min_timeout` or
`safety_margin` is negative, or if `safety_margin >= total_seconds`.

| Member | Returns | Notes |
|---|---|---|
| `remaining()` | `float` | Seconds left of the usable budget. Negative past the deadline. Never raises. |
| `elapsed()` | `float` | Seconds since construction. Never raises. |
| `expired()` | `bool` | `remaining() <= 0`, so exactly zero counts as expired. Never raises. |
| `timeout_for(cap=None, min_timeout=None, reserve_for_next=0.0)` | `float` | The timeout for the next call. **Raises `DeadlineExceededError`** when nothing is left. `min_timeout` here overrides the instance's. |
| `check_expired()` | `None` | Raises `DeadlineExceededError` if `expired()`. |
| `total_seconds` (property) | `float` | The **usable** budget — the constructor argument minus `safety_margin`. |

### `BudgetContext`

`BudgetContext(budget, call_caps)` takes both positionally and both are required. Use the
classmethod instead:

`BudgetContext.create(total_seconds, call_caps=None, *, min_timeout=0.1, safety_margin=0.0)`
— builds the `DeadlineBudget` for you; `call_caps=None` means an empty mapping.

| Member | Returns | Notes |
|---|---|---|
| `timeout_for_call(call_name, reserve_for_next=0.0)` | `float` | `budget.timeout_for(cap=call_caps.get(call_name), reserve_for_next=…)`. An unknown name is not an error — it means no cap. |
| `check_expired()` / `remaining()` / `elapsed()` / `expired()` | as above | Straight delegation to the budget. |
| `budget` (property) | `DeadlineBudget` | The underlying budget, for anything the context does not expose. |
| `call_caps` (property) | `dict[str, float]` | The context's own mapping — a copy of what was passed in, live for every later call on this context. |

There is no `timeout_for` on `BudgetContext` and no `call_caps` mutator; reach through
`ctx.budget`, or mutate `ctx.call_caps` in place.

### `deadline_budget.contrib.settings` — extra `settings`, needs Pydantic 2

Plain `pydantic.BaseModel` classes. Nest them in your own settings object; they read no
environment variables of their own.

| Name | Fields |
|---|---|
| `OperationDeadlineConfig` | `budget_timeout: float = 10.0` (1.0–60.0), `safety_margin: float | None = None` (0.0–5.0), `min_timeout: float | None = None` (0.01–1.0), `calls_caps: dict[str, float] = {}` (also accepted as `call_caps` on input) |
| `BaseDeadlineSettings` | `operations: dict[str, OperationDeadlineConfig] = {}`, `default_budget_timeout: float = 10.0`, `default_safety_margin: float = 0.5`, `default_min_timeout: float = 0.1` |

`BaseDeadlineSettings.config_for_operation(operation)` returns the entry for that name, or
— when there is none — a fresh `OperationDeadlineConfig(budget_timeout=default_budget_timeout)`
whose `safety_margin` and `min_timeout` are `None` and whose `calls_caps` is empty.

### `deadline_budget.contrib.dishka` — extra `dishka`

| Name | What it is |
|---|---|
| `DeadlineContextFactory(settings)` | `.create_for_operation(operation)` builds a `BudgetContext` from the config for that operation, resolving each `None` override against the global default. `operation` may be a string or anything with a `.value` (a `str` enum). |
| `DeadlineProvider()` | A `dishka.Provider` at `Scope.APP` providing exactly one thing: `DeadlineContextFactory`. It requires a `DeadlineSettingsProtocol` binding from one of your own providers. |
| `DeadlineSettingsProtocol` | `runtime_checkable` protocol: `default_safety_margin`, `default_min_timeout`, `config_for_operation(operation)`. |
| `OperationDeadlineConfigProtocol` | `runtime_checkable` protocol: `budget_timeout`, `calls_caps`, `safety_margin`, `min_timeout`. |

`BaseDeadlineSettings` satisfies `DeadlineSettingsProtocol` structurally; nothing forces
you to use it.

## Crossing a process boundary

This is the part that is easy to get wrong, because the library gives you no help and no
error when you get it wrong.

**The object never travels.** `DeadlineBudget` stores a reading of `time.monotonic()`,
whose zero point is arbitrary and meaningful only inside the process that took it. A budget
that is pickled, JSON-encoded or handed to a subprocess arrives with a start instant that
means nothing there; the arithmetic still runs and still returns numbers, and every one of
them is wrong. There is no wire format, no header helper and no `from_deadline(...)`
constructor, because there is nothing correct to reconstruct from.

**The number travels.** The caller computes the callee's deadline and sends it as whatever
the transport already calls a timeout — a gRPC deadline, an HTTP header, a field on a task
payload:

```python
# caller
timeout = ctx.timeout_for_call("billing.charge", reserve_for_next=0.5)
await billing.charge(order_id, timeout=timeout)          # and put `timeout` on the wire

# callee, first line of the handler
budget = DeadlineBudget(total_seconds=deadline_from_request, safety_margin=0.2)
```

The callee's budget starts after transit, so it is strictly shorter than what the caller
had left — that is the safe direction. Pay for the response leg on the caller's side with
`reserve_for_next`, or on the callee's side with `safety_margin`; nothing does it for you.

**In-process, propagation is a function argument.** There is no context variable and
nothing ambient. A nested step gets the budget because you passed the same `BudgetContext`
into it. Building a second context inside a nested step — including by calling
`DeadlineContextFactory.create_for_operation` again — starts a second countdown from now
and silently doubles the deadline the request was given.

**Fan-out does not divide the budget.** Under `asyncio.gather`, each branch asks the same
budget and each gets the whole remaining time, which is right for calls that genuinely run
at the same time and wrong for anything sequential hiding behind one branch. Split it
yourself with `cap` or `reserve_for_next`.

## When the budget runs out

Exhaustion is a fact you can observe, not an event that fires. Nothing in the library is
watching the clock.

1. `remaining()` goes negative and `expired()` turns `True` at exactly zero. Neither
   raises, and neither changes anything.
2. The next `timeout_for()` or `timeout_for_call()` raises `DeadlineExceededError` instead
   of returning a number. `check_expired()` raises the same error. Those four methods are
   the only place the library ever raises it.
3. **An in-flight call is not cancelled.** The timeout you already handed it is the only
   thing bounding it; the budget cannot reach into a call it does not know about.
4. **A downstream call that times out raises the client's own error** — `TimeoutError`,
   `httpx.ReadTimeout`, `grpc.aio.AioRpcError` — never `DeadlineExceededError`. If you want
   one error type at the edge, translate it yourself.
5. The last call before exhaustion can overrun it, because `timeout_for` hands out
   `min_timeout` even when less than that is left. The `safety_margin` pays for that.

## Rules that hold or break the code

1. **`total_seconds` in is not `total_seconds` out.**
   `DeadlineBudget(total_seconds=10.0, safety_margin=0.5).total_seconds` is `9.5`, and
   `DeadlineExceededError.budget_seconds` is `9.5` too. Both report the usable budget.
   Keep the number you passed if you need it for a log line or a metric.
2. **The clock starts in `__init__`.** Construct the budget where the request starts, not
   where the container is wired. An APP-scoped or module-level `DeadlineBudget` has been
   counting down since the process booted and is permanently expired.
3. **`min_timeout` outranks the remaining budget.** `max(remaining - reserve_for_next,
   min_timeout)` means a call can be granted more time than the budget has left. This is
   deliberate — a 3 ms timeout is useless — but it is why a budget with no safety margin
   can overrun.
4. **`cap` outranks `min_timeout`.** The cap is applied last, so `timeout_for(cap=0.05)`
   with `min_timeout=0.1` returns `0.05`. The floor is not a guarantee.
5. **`reserve_for_next` is best effort, and only for the one call.** It reserves nothing:
   it subtracts from this call's timeout, and when the difference falls under the floor the
   floor wins and the reservation quietly vanishes. Two calls in a row both reserving 2s
   reserve 2s, not 4s.
6. **Asking costs nothing.** `timeout_for` does not consume, decrement or record anything.
   Only the passage of time moves the budget, so a number you computed and did not use is
   already stale.
7. **The returned number does nothing unless you pass it on.** `budget.timeout_for(cap=5.0)`
   on its own line is dead code. The library enforces no timeout anywhere.
8. **An unknown `call_name` is not an error.** `timeout_for_call("typo")` returns the full
   remaining budget, uncapped. Caps are looked up with `dict.get`, so a misspelled or
   renamed key removes the ceiling instead of reporting it. Keep the keys in one constant.
9. **The settings field is `calls_caps`; the context argument is `call_caps`.**
   `OperationDeadlineConfig` accepts either spelling as input and stores the value under
   `calls_caps` — that is the name to read it back under, the name it dumps to, and the
   name `OperationDeadlineConfigProtocol` requires. Every other field is matched exactly,
   and Pydantic still ignores keys it does not know.
10. **`BaseDeadlineSettings` is a `BaseModel`, not a `BaseSettings`,** despite the extra
    being called `settings`. It reads no environment and no `.env`; nest it inside your own
    `pydantic_settings.BaseSettings` if you want that.
11. **The settings models clamp what the core accepts.** `budget_timeout` is 1.0–60.0,
    `safety_margin` 0.0–5.0, `min_timeout` 0.01–1.0. `DeadlineBudget` itself takes any
    positive float, so a 90-second budget is legal in code and a validation error in
    configuration.
12. **A budget is immutable after construction**, so reading it from several tasks or
    threads is safe. What is not safe is assuming those readers are sharing the time: see
    fan-out above.
13. **`ctx.call_caps` is the context's own dict.** The mapping handed to `BudgetContext`
    is copied at construction, so changing the dict you passed to `create()` afterwards
    changes nothing — and a context built from settings cannot write back into them.
    Mutating what the property returns does change the caps for every later call, on that
    context only.
14. **The contrib modules are not re-exported.** `deadline_budget` exports exactly
    `DeadlineBudget`, `BudgetContext` and `DeadlineExceededError`. Everything else is
    imported from `deadline_budget.contrib.settings` or `deadline_budget.contrib.dishka`,
    each of which imports its optional dependency at module level and raises `ImportError`
    without it.
15. **Test it by patching the clock, not by sleeping.** `DeadlineBudget` reads
    `time.monotonic()` on every call; `patch("time.monotonic")` gives deterministic tests.

## Common mistakes

```python
# WRONG — the budget object sent to another service
await billing.charge(order_id, budget=pickle.dumps(ctx.budget))

# RIGHT — the number sent, a new budget built on arrival
await billing.charge(order_id, timeout=ctx.timeout_for_call("billing.charge"))
# ... in the callee:
budget = DeadlineBudget(total_seconds=timeout_from_request, safety_margin=0.2)
```

```python
# WRONG — a new context per step, so each step restarts the countdown
async def step_two(factory: DeadlineContextFactory) -> None:
    ctx = factory.create_for_operation("signup")
    ...

# RIGHT — one context per request, passed down
async def step_two(ctx: BudgetContext) -> None:
    ...
```

```python
# WRONG — computing a timeout and not using it, then expecting to be interrupted
budget.timeout_for(cap=5.0)
await slow_call()                 # unbounded; the budget cannot stop it

# RIGHT
await slow_call(timeout=budget.timeout_for(cap=5.0))
```

```python
# WRONG — expecting the library's error when a downstream call times out
try:
    await identity.create_user(email, timeout=ctx.timeout_for_call("identity.create_user"))
except DeadlineExceededError:
    ...                           # never reached: httpx/grpc/asyncio raise their own

# RIGHT — DeadlineExceededError guards the call, the client's error ends it
try:
    timeout = ctx.timeout_for_call("identity.create_user")   # raises if nothing is left
    await identity.create_user(email, timeout=timeout)
except DeadlineExceededError:
    raise GatewayTimeout from None
except TimeoutError:
    raise UpstreamTimeout from None
```

```python
# WRONG — reading back what you put in
budget = DeadlineBudget(total_seconds=10.0, safety_margin=0.5)
log.info("budget %.1fs", budget.total_seconds)          # 9.5, not 10.0

# RIGHT
TOTAL = 10.0
budget = DeadlineBudget(total_seconds=TOTAL, safety_margin=0.5)
log.info("budget %.1fs (usable %.1fs)", TOTAL, budget.total_seconds)
```

## Errors

`DeadlineExceededError` is the only exception the library defines. It derives from
`Exception`, carries `budget_seconds` (the usable budget) and `elapsed_seconds`, and is
raised by `DeadlineBudget.timeout_for`, `DeadlineBudget.check_expired`,
`BudgetContext.timeout_for_call` and `BudgetContext.check_expired`.

Two properties of it are deliberate and worth knowing:

* It initialises `Exception` directly rather than through `super()`, so it can be the
  **first** base of a class that also inherits a domain error whose `__init__` takes
  something other than a message. List it first and call each base's `__init__` explicitly;
  see [advanced usage](guide/advanced.md).
* It defines `__reduce__`, so it survives `pickle` and `copy` with both attributes intact —
  `BaseException` would otherwise restore it from `args`, which holds the formatted message.

Bad arguments raise plain `ValueError` from `DeadlineBudget.__init__`
(`total_seconds <= 0`, negative `min_timeout` or `safety_margin`,
`safety_margin >= total_seconds`), and the contrib models raise
`pydantic.ValidationError` for a field outside its bounds.

## Documentation map

Fetch a page when the task is the one named beside it.

| Page | Read it when |
|---|---|
| [Overview](index.md) | you want the one-paragraph pitch and the two entry points side by side |
| [Quickstart](guide/quickstart.md) | writing the first integration: both APIs, every parameter explained, a registration flow end to end |
| [Configuration](guide/configuration.md) | choosing `total_seconds`, `safety_margin`, `min_timeout` and caps, and picking between `DeadlineBudget` and `BudgetContext` |
| [Advanced usage](guide/advanced.md) | nested orchestrations, retries under a budget, dynamic caps, metrics and tracing, composing `DeadlineExceededError` into your own error hierarchy, testing with a patched clock |
| [Integrations](guide/integrations.md) | wiring the Pydantic settings models or the Dishka provider into an application |
| [API reference](reference/index.md) | an exact signature, field or docstring — HTML only, see above |
| [Changelog](changelog.md) | what changed between versions |
