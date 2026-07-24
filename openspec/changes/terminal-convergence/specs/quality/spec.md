## ADDED Requirements

### Requirement: Terminal Source Budget
Terminal Python ELOC MUST be at most 54,000 and terminal global owned-source ELOC MUST be at most 68,000; measurement MUST include product, tests, tools, scripts, executable configuration, templates, and generated owned source while excluding comments, blank lines, and docstrings.

#### Scenario: Logic is moved from Python to generated configuration
- **WHEN** owned executable semantics move carriers without being deleted
- **THEN** global owned-source measurement still counts the semantics and grants no false deletion credit

### Requirement: Direct Source Measurement
Source measurement MUST use scc, canonical formatters, and Python AST/tokenize cross-checks through one direct deterministic implementation and MUST NOT require a private worker protocol, replay runtime, or shadow verdict.

#### Scenario: Independent measurements disagree
- **WHEN** canonical counters differ outside the declared tolerance
- **THEN** the budget verdict blocks with the disagreement evidence rather than selecting a favorable count

### Requirement: Singular Quality Ownership
Ruff, Pyright strict, rumdl, dprint, shfmt/ShellCheck, ast-grep, and import-linter MUST be the sole terminal owners of their declared properties; all warnings and production suppressions MUST be hard failures.

#### Scenario: CI emits a deprecation warning
- **WHEN** any local or provider quality command emits an unapproved warning
- **THEN** the quality gate fails even if the command exit code would otherwise be zero

### Requirement: Capability-preserving Test Floor
Global branch coverage MUST be at least 95%, authority/CAS/transition reducers MUST be 100%, and critical pure reducers MUST pass bounded mutation testing without retaining tests whose only purpose is branch reachability.

#### Scenario: A test raises coverage without asserting behavior
- **WHEN** deletion of the test leaves all contract, property, mutation, and adopter proofs unchanged
- **THEN** the test is classified as removable rather than product evidence
