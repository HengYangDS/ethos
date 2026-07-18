## ADDED Requirements

### Requirement: Portable configuration-lint interpreter resolution

ETHOS configuration-lint owner scripts SHALL run inline Python standard-library
validation through an explicit bounded interpreter chain: `ETHOS_PYTHON`, then
`PYTHON`, then `python3`. They SHALL NOT require a bare `python` command alias.
Targeted TOML-only invocations SHALL retain all TOML checks even when no JSON or
YAML target is present.

#### Scenario: standalone runtime lacks a python alias

- **GIVEN** a standalone configuration-lint fixture exposes `python3` but no
  bare `python` executable
- **WHEN** its targeted TOML check runs with runtime bootstrap already marked
- **THEN** the TOML parser, newline, whitespace, Taplo format, and Taplo lint
  checks complete successfully
- **AND** the runner does not invoke the absent `python` alias.

### Requirement: Isolated sharded Python test evidence preserves the quality floor

ETHOS SHALL permit the Python test owner script to use an explicit isolated
evidence root, pytest base temporary directory, and finite shard count while
preserving the same selected tests, coverage combination, coverage floor, and
HEAD-stability check as its unsharded execution.

#### Scenario: isolated sharded execution completes

- **WHEN** the Python test owner script runs with isolated evidence and
  temporary paths plus a positive shard count
- **THEN** it combines all completed shard coverage before enforcing the
  declared coverage floor
- **AND** it leaves no trust-bearing claim that a hosted provider ran.
