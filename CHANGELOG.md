# Changelog

All notable project changes will be documented in this file. The project follows
[Semantic Versioning](https://semver.org/) once its public API stabilises.

## [Unreleased]

### Added

- Modern `oughtlib` packaging for the `ought` import package, targeting Python
  3.11 and newer with no runtime dependencies.
- Hierarchical `Settings` with explicit source precedence, TOML loading,
  environment nesting and scalar parsing, nested attribute and mapping access,
  redacted `Secret` values, typed `require()`, and context-local overrides.
- A typed `nursery()` wrapper over `asyncio.TaskGroup`.
- An insertion-ordered mutable `MultiMap` with first-value mapping semantics.
- Strict linting, typing, doctest, coverage, documentation, build, and CI checks.

### Changed

- Hardened `MultiMap` mutation against unhashable and non-reflexive keys while
  preserving dictionary-compatible key identity.
- Matched the Nursery lifecycle to `asyncio.TaskGroup` while child tasks drain.
- Rejected cyclic Settings containers with actionable source errors and made
  environment source-shape validation explicit.
- Clarified structural immutability, TOML environment values, dotted sensitive
  paths, and task-local override inheritance.
