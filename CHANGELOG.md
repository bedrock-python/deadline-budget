# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2](https://github.com/bedrock-python/deadline-budget/compare/deadline-budget-v0.1.1...deadline-budget-v0.1.2) (2026-08-28)


### Bug Fixes

* make DeadlineExceededError picklable ([#10](https://github.com/bedrock-python/deadline-budget/issues/10)) ([ed5c739](https://github.com/bedrock-python/deadline-budget/commit/ed5c739b726fdf0ba724789a47b3d30de3f649e1))


### Documentation

* fix broken examples and API reference links ([#11](https://github.com/bedrock-python/deadline-budget/issues/11)) ([61ba7d5](https://github.com/bedrock-python/deadline-budget/commit/61ba7d5ccdc1a606fac3b8d9977cb0b6e1b5df0c))

## [0.1.1](https://github.com/bedrock-python/deadline-budget/compare/deadline-budget-v0.1.0...deadline-budget-v0.1.1) (2026-08-28)


### Bug Fixes

* make DeadlineExceededError safe under multiple inheritance ([#7](https://github.com/bedrock-python/deadline-budget/issues/7)) ([465d726](https://github.com/bedrock-python/deadline-budget/commit/465d72636609ed2a56e79a6ae64e3edbace2310f)), closes [#6](https://github.com/bedrock-python/deadline-budget/issues/6)
* update publish workflow, release-please version search, gitignore ([#3](https://github.com/bedrock-python/deadline-budget/issues/3)) ([3a2f527](https://github.com/bedrock-python/deadline-budget/commit/3a2f527fde4a0ca26d7a283c6d8c45a6486818c3))

## 0.1.0 (2026-05-09)

Initial release of deadline-budget library.

### Features

* Core deadline budget tracking with `DeadlineBudget` class
* `BudgetContext` for orchestration timeouts with per-call caps
* Optional Pydantic settings integration (`deadline-budget[settings]`)
* Optional Dishka DI provider (`deadline-budget[dishka]`)
* 100% test coverage with BDD naming conventions
* Full type hints support (py.typed marker)
