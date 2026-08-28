# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Bug Fixes

* `DeadlineExceededError` now initialises `Exception` directly instead of via `super()`, so it can be used as the
  first base of a class that also inherits from an exception with an incompatible `__init__` signature
  ([#6](https://github.com/bedrock-python/deadline-budget/issues/6))

## 0.1.0 (2026-05-09)

Initial release of deadline-budget library.

### Features

* Core deadline budget tracking with `DeadlineBudget` class
* `BudgetContext` for orchestration timeouts with per-call caps
* Optional Pydantic settings integration (`deadline-budget[settings]`)
* Optional Dishka DI provider (`deadline-budget[dishka]`)
* 100% test coverage with BDD naming conventions
* Full type hints support (py.typed marker)
