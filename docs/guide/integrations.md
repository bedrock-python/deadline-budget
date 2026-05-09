# Integrations

Extensions for deadline-budget with popular libraries.

## Pydantic Settings

Install with: `pip install deadline-budget[settings]`

### Configuration Classes

```python
from deadline_budget.contrib.settings import BaseDeadlineSettings, OperationDeadlineConfig

# Define settings
class AppSettings(BaseModel):
    deadline: BaseDeadlineSettings = Field(
        default_factory=lambda: BaseDeadlineSettings(
            default_budget_timeout=10.0,
            default_safety_margin=0.5,
            default_min_timeout=0.1,
            operations={
                "signup_confirm": OperationDeadlineConfig(
                    budget_timeout=15.0,
                    safety_margin=1.0,
                    calls_caps={
                        "identity_create_user": 3.0,
                        "credential_set_password": 3.0,
                        "verification_send_code": 2.0,
                    },
                ),
                "login": OperationDeadlineConfig(
                    budget_timeout=5.0,
                    calls_caps={
                        "identity_get_user": 1.0,
                        "credential_verify_password": 2.0,
                    },
                ),
            },
        )
    )
```

### Using Configuration

```python
settings = AppSettings()

# Get configuration for specific operation
config = settings.deadline.config_for_operation("signup_confirm")

# Create BudgetContext from config
ctx = BudgetContext.create(
    total_seconds=config.budget_timeout,
    safety_margin=config.safety_margin or settings.deadline.default_safety_margin,
    min_timeout=config.min_timeout or settings.deadline.default_min_timeout,
    call_caps=config.calls_caps,
)
```

## Dishka DI Provider

Install with: `pip install deadline-budget[dishka]`

### Basic Setup

```python
from dishka import make_async_container
from deadline_budget.contrib.dishka import DeadlineProvider, DeadlineContextFactory

# Create container
container = make_async_container(
    DeadlineProvider(),
    # ... other providers
)

# Use in application
async with container() as request_container:
    factory = await request_container.get(DeadlineContextFactory)
    ctx = factory.create_for_operation("signup_confirm")
```

### Custom Settings Provider

```python
from dishka import Provider, Scope, provide
from deadline_budget.contrib.dishka import DeadlineSettingsProtocol

class SettingsProvider(Provider):
    scope = Scope.APP

    @provide
    def get_deadline_settings(self, app_settings: AppSettings) -> DeadlineSettingsProtocol:
        """Provide deadline settings from app settings."""
        return app_settings.deadline

# Register both providers
container = make_async_container(
    SettingsProvider(),
    DeadlineProvider(),
)
```

### Using in Use Cases

```python
from deadline_budget.contrib.dishka import DeadlineContextFactory

class SignupConfirmUseCase:
    def __init__(
        self,
        uow: AsyncUnitOfWork,
        deadline_factory: DeadlineContextFactory,
    ) -> None:
        self._uow = uow
        self._deadline_factory = deadline_factory

    async def execute(self, email: str, password: str) -> User:
        # Create budget context for this operation
        ctx = self._deadline_factory.create_for_operation("signup_confirm")

        async with self._uow.transaction() as tx:
            user = await tx.users.create(
                email=email,
                timeout=ctx.timeout_for_call("identity_create_user"),
            )

            await tx.credentials.set_password(
                user_id=user.id,
                password=password,
                timeout=ctx.timeout_for_call("credential_set_password"),
            )

            ctx.check_expired()
            return user
```

### Advanced: Operation Enums

```python
from enum import Enum

class Operation(str, Enum):
    SIGNUP_CONFIRM = "signup_confirm"
    LOGIN = "login"
    PASSWORD_RESET = "password_reset"

# Use enum with factory
ctx = deadline_factory.create_for_operation(Operation.SIGNUP_CONFIRM)
```

### Protocol Interface

The Dishka provider uses protocols for flexibility:

```python
from deadline_budget.contrib.dishka import (
    DeadlineSettingsProtocol,
    OperationDeadlineConfigProtocol,
)

# Implement custom settings
class CustomSettings:
    @property
    def default_safety_margin(self) -> float:
        return 0.5

    @property
    def default_min_timeout(self) -> float:
        return 0.1

    def config_for_operation(self, operation: str) -> OperationDeadlineConfigProtocol:
        # Custom logic here
        ...
```

## Complete Example

```python
from pydantic import BaseModel, Field
from dishka import make_async_container, Provider, Scope, provide

from deadline_budget.contrib.settings import BaseDeadlineSettings, OperationDeadlineConfig
from deadline_budget.contrib.dishka import DeadlineProvider, DeadlineContextFactory

# 1. Define settings
class AppSettings(BaseModel):
    deadline: BaseDeadlineSettings = Field(
        default_factory=lambda: BaseDeadlineSettings(
            operations={
                "signup": OperationDeadlineConfig(
                    budget_timeout=10.0,
                    calls_caps={
                        "identity_create": 3.0,
                        "credential_set": 3.0,
                    },
                ),
            },
        )
    )

# 2. Create settings provider
class AppProvider(Provider):
    scope = Scope.APP

    @provide
    def get_settings(self) -> AppSettings:
        return AppSettings()

    @provide
    def get_deadline_settings(self, settings: AppSettings):
        return settings.deadline

# 3. Create container
container = make_async_container(
    AppProvider(),
    DeadlineProvider(),
)

# 4. Use in application
async with container() as request_container:
    factory = await request_container.get(DeadlineContextFactory)
    ctx = factory.create_for_operation("signup")

    # Use context
    timeout = ctx.timeout_for_call("identity_create")
    print(f"Timeout: {timeout}s")
```
