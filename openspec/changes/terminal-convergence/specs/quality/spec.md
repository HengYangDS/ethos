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

### Requirement: Monotone Changed-scope Admission
Intermediate authoring admission MUST compare the current tree with its exact
merge-base through the same direct measurement owner. A non-increasing measured
change MUST NOT be blocked only by unrelated historical debt, while terminal
closeout MUST still satisfy every hard repository budget.

#### Scenario: A change deletes measured source while the repository exceeds its terminal limit
- **WHEN** each governed metric coordinate is unchanged or reduced from the exact merge-base
- **THEN** authoring admission allows the change to continue
- **AND** terminal proof remains blocked until the repository itself meets every limit

#### Scenario: A change attempts to borrow an unrelated surplus
- **WHEN** one category or metric grows and another category or metric shrinks
- **THEN** the growing coordinate is not compensated by the unrelated reduction

#### Scenario: The baseline or inventory drifts
- **WHEN** merge-base, current tree, measured inventory, or metric ownership cannot be reproduced
- **THEN** changed-scope admission resolves to block or unknown and performs no write

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

## MODIFIED Requirements

### Requirement: Semantic And Physical Isomorphism

ETHOS SHALL gate repository-owned Python as semantic architecture rather than as
a file-count topology. Every module and package MUST state one narrow concept,
one authority owner, and one primary reason to change through its name, path,
symbols, and dependencies. The same semantic invariants MUST cover product
source, tests, tools, and agent scripts while respecting each carrier's native
naming syntax.

Ambiguous names MUST fail unless a closed machine role contract proves an
irreducible kernel or report aggregator. CLI commands MUST have one declaration
owner, and compatibility facades MUST NOT satisfy this requirement. File count,
directory width, ELOC, and punctuation MUST NOT mint a semantic split or waiver.

#### Scenario: A generic module has no closed semantic contract

- **WHEN** the module-layout gate observes `core`, `common`, `shared`, `utils`,
  `helpers`, `base`, `manager`, `service`, or another configured ambiguous name
- **THEN** the module must be absorbed, precisely renamed, split on a real
  semantic axis, or deleted
- **AND** splitting only to satisfy ELOC or retaining the old path as a facade is
  not remediation

#### Scenario: Semantic module layout is reported and enforced

- **WHEN** `ethos prove --gate module-layout --json` runs
- **THEN** ETHOS scans tracked and non-ignored untracked Python across the whole
  repository while excluding deleted and ignored runtime files
- **AND** it reports ambiguous module and package names, multiple command owners,
  private import aliases, package `__init__.py` facades, ordinary module facades,
  dynamic compatibility facades, package-root submodule imports, and cross-module
  private imports against `.config/checks/module-layout/policy.toml`
- **AND** product-package topology has a narrower explicit scope so pytest and
  tool naming syntax is not mistaken for product architecture
- **AND** the policy has no baseline, allowlist, file-count threshold, or ELOC
  threshold that converts a semantic defect into accepted debt or mints a split
- **AND** every finding blocks and requires absorb, precise rename, semantic split,
  or deletion
- **AND** hosted CI, pre-commit, local CI, and proof invoke the reusable
  `tools/ci/scripts/run-module-layout.sh` owner script instead of duplicating the
  policy inline
