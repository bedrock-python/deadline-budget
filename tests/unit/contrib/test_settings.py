"""Tests for Pydantic settings module."""

import pytest

from deadline_budget.contrib.settings import BaseDeadlineSettings, OperationDeadlineConfig

pytestmark = pytest.mark.unit


def test__operation_config__defaults__returns_expected_values() -> None:
    # Arrange & Act
    config = OperationDeadlineConfig()

    # Assert
    assert config.budget_timeout == 10.0
    assert config.safety_margin is None
    assert config.min_timeout is None
    assert config.calls_caps == {}


def test__operation_config__with_custom_values__stores_all_fields() -> None:
    # Arrange
    custom_values = {
        "budget_timeout": 15.0,
        "safety_margin": 1.0,
        "min_timeout": 0.2,
        "calls_caps": {
            "identity_create_user": 3.0,
            "credential_set_password": 2.0,
        },
    }

    # Act
    config = OperationDeadlineConfig(**custom_values)

    # Assert
    assert config.budget_timeout == 15.0
    assert config.safety_margin == 1.0
    assert config.min_timeout == 0.2
    assert config.calls_caps == {
        "identity_create_user": 3.0,
        "credential_set_password": 2.0,
    }


@pytest.mark.parametrize(
    "invalid_timeout,reason",
    [
        (0.5, "too small"),
        (70.0, "too large"),
    ],
)
def test__operation_config__budget_timeout_out_of_range__raises_validation_error(
    invalid_timeout: float, reason: str
) -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValueError):
        OperationDeadlineConfig(budget_timeout=invalid_timeout)


@pytest.mark.parametrize(
    "invalid_margin,reason",
    [
        (-0.1, "negative"),
        (6.0, "too large"),
    ],
)
def test__operation_config__safety_margin_out_of_range__raises_validation_error(
    invalid_margin: float, reason: str
) -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValueError):
        OperationDeadlineConfig(safety_margin=invalid_margin)


@pytest.mark.parametrize(
    "invalid_min_timeout,reason",
    [
        (0.001, "too small"),
        (2.0, "too large"),
    ],
)
def test__operation_config__min_timeout_out_of_range__raises_validation_error(
    invalid_min_timeout: float, reason: str
) -> None:
    # Arrange & Act & Assert
    with pytest.raises(ValueError):
        OperationDeadlineConfig(min_timeout=invalid_min_timeout)


def test__base_deadline_settings__defaults__returns_expected_values() -> None:
    # Arrange & Act
    settings = BaseDeadlineSettings()

    # Assert
    assert settings.operations == {}
    assert settings.default_budget_timeout == 10.0
    assert settings.default_safety_margin == 0.5
    assert settings.default_min_timeout == 0.1


def test__base_deadline_settings__with_operations__stores_all_configs() -> None:
    # Arrange
    operations = {
        "signup": OperationDeadlineConfig(
            budget_timeout=15.0,
            calls_caps={"identity_create": 3.0},
        ),
        "login": OperationDeadlineConfig(
            budget_timeout=5.0,
            calls_caps={"identity_get": 1.0},
        ),
    }

    # Act
    settings = BaseDeadlineSettings(
        operations=operations,
        default_budget_timeout=12.0,
        default_safety_margin=0.8,
        default_min_timeout=0.2,
    )

    # Assert
    assert len(settings.operations) == 2
    assert settings.operations["signup"].budget_timeout == 15.0
    assert settings.operations["login"].budget_timeout == 5.0
    assert settings.default_budget_timeout == 12.0
    assert settings.default_safety_margin == 0.8
    assert settings.default_min_timeout == 0.2


def test__base_deadline_settings__config_for_operation_existing__returns_configured_operation() -> None:
    # Arrange
    settings = BaseDeadlineSettings(
        operations={
            "signup": OperationDeadlineConfig(
                budget_timeout=15.0,
                calls_caps={"identity_create": 3.0},
            ),
        }
    )

    # Act
    config = settings.config_for_operation("signup")

    # Assert
    assert config.budget_timeout == 15.0
    assert config.calls_caps == {"identity_create": 3.0}


def test__base_deadline_settings__config_for_operation_missing__returns_default_config() -> None:
    # Arrange
    settings = BaseDeadlineSettings(
        default_budget_timeout=12.0,
        operations={
            "signup": OperationDeadlineConfig(budget_timeout=15.0),
        },
    )

    # Act
    config = settings.config_for_operation("unknown_operation")

    # Assert
    assert config.budget_timeout == 12.0
    assert config.calls_caps == {}
    assert config.safety_margin is None
    assert config.min_timeout is None


@pytest.mark.parametrize(
    "field,invalid_value,reason",
    [
        ("default_budget_timeout", 0.5, "too small"),
        ("default_safety_margin", -0.1, "negative"),
        ("default_min_timeout", 0.001, "too small"),
    ],
)
def test__base_deadline_settings__global_defaults_out_of_range__raises_validation_error(
    field: str, invalid_value: float, reason: str
) -> None:
    # Arrange
    kwargs = {field: invalid_value}

    # Act & Assert
    with pytest.raises(ValueError):
        BaseDeadlineSettings(**kwargs)
