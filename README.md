# deadline-budget

Request deadline budget tracking for distributed orchestrations

[![PyPI](https://img.shields.io/pypi/v/deadline-budget?color=blue)](https://pypi.org/project/deadline-budget/)
[![Python](https://img.shields.io/pypi/pyversions/deadline-budget)](https://pypi.org/project/deadline-budget/)
[![License](https://img.shields.io/github/license/bedrock-python/deadline-budget)](LICENSE)
[![CI](https://github.com/bedrock-python/deadline-budget/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/bedrock-python/deadline-budget/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/bedrock-python/deadline-budget/graph/badge.svg)](https://codecov.io/gh/bedrock-python/deadline-budget)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://bedrock-python.github.io/deadline-budget/)

> [!TIP]
> **Building this with an AI assistant?** Hand it
> **[one page](https://bedrock-python.github.io/deadline-budget/agents/)** instead of the
> whole site: the whole API surface, how a budget crosses a process boundary and what
> happens when one runs out, the rules that break code when they are broken, the mistakes
> models actually make, and a map of which page to fetch for the rest. Every docs page is
> also served as raw Markdown at its own URL, and a **Copy page** button at the top of each
> one hands it straight to a chat window.

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

## Quick start

```python
from deadline_budget import BudgetContext

# Define per-call timeout caps
call_caps = {
    "identity_create_user": 3.0,
    "credential_set_password": 3.0,
    "verification_verify_code": 2.0,
}

# Create context with total budget (10s total, 0.5s safety margin = 9.5s usable)
ctx = BudgetContext.create(
    total_seconds=10.0,
    safety_margin=0.5,
    min_timeout=0.1,
    call_caps=call_caps,
)

# Get timeout for each call (uses specific cap or remaining budget)
await identity_service.create_user(..., timeout=ctx.timeout_for_call("identity_create_user"))
await credential_service.set_password(..., timeout=ctx.timeout_for_call("credential_set_password"))
await verification_service.confirm(..., timeout=ctx.timeout_for_call("verification_verify_code"))

# Check if budget exhausted
ctx.check_expired()  # Raises DeadlineExceededError if expired
```

## Documentation

Full documentation at [bedrock-python.github.io/deadline-budget](https://bedrock-python.github.io/deadline-budget/).

- [For AI agents](https://bedrock-python.github.io/deadline-budget/agents/) — the whole API
  surface, the rules that break code when broken and a map of the rest, on one page to hand
  to a coding assistant

## License

Apache 2.0 — see [LICENSE](LICENSE).
