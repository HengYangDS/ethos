---
subject: ethos:decision:source-budget-non-compensation
role: decision
state: canonical
relations:
  current_owner: ../../.config/checks/format/selection.toml
---

# Source Budget Non-Compensation

Status: canonical rationale. Executable thresholds are owned by quality
configuration.

Purpose: preserve why unrelated source classes cannot compensate for one
another and why size remains a tripwire rather than a design target.

See also: [Documentation Root](../README.md),
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md),
and `.config/checks/format/selection.toml`.

## Context

A single repository-wide line budget allowed deletion in one carrier to hide
growth in an unrelated owner. It also rewarded minification, moving behavior
into declarations or literals, and splitting files to satisfy a surface metric.
The opposite design—a private metric DSL with parser, replay, shadow, debt, and
migration machinery—made measurement itself a second product.

The useful invariant is narrower: unexplained growth must be visible where its
semantic owner changes, but no number can decide whether an abstraction or
carrier is necessary.

## Decision

Measure owned source deterministically by carrier and Python role, enforce local
ceilings plus a global ceiling, and cross-check measurements independently.
Structural duplication, competing owners, and semantic overlap decide deletion;
line count alone does not.

Budgets are non-compensating: a surplus in tests, documentation, or one source
role cannot pay for excess in another. Per-file limits remain readability
tripwires. A breach triggers semantic review—delete, absorb, rename, or split by
real ownership—not mechanical file fragmentation.

## Consequences

- Every governed carrier must be classified into one measured owner or fail
  closed; hidden exclusions cannot make a budget green.
- Budget changes require evidence at the owner that grows and cannot be justified
  by unrelated repository shrinkage.
- Direct native measurement and independent cross-checks are preferred over a
  custom metric runtime.
- Passing a size gate never proves architectural quality; semantic ownership and
  behavior-preserving tests remain authoritative.

## Rejected Alternatives

- **One aggregate repository budget:** rejected because unrelated domains can
  subsidize one another and obscure the source of growth.
- **Raw LOC as semantic currency:** rejected because formatting, literals, and
  carrier movement can game it.
- **A private metric vector runtime:** rejected because its parser, replay,
  shadow, debt, and migration machinery exceeded the invariant it protected.
- **Splitting solely to satisfy a threshold:** rejected because it preserves the
  same mixed ownership under more physical entities.

## Evidence

- `.config/checks/format/selection.toml` owns current classifications,
  thresholds, native commands, and the independent `scc` cross-check.
- `src/ethos/domain/source_budget/measurement.py` and
  `measurement_policy.py` implement direct deterministic measurement.
- `tests/unit/domain/test_source_budget.py` and
  `test_source_budget_public_determinism.py` cover non-compensation,
  classification, and deterministic output.
- [Module Layout And Visibility Rules](../../rules/module_layout.md) prevents
  size thresholds from authorizing suffix-flat or metric-driven splits.

## Revisit And Retirement

Revisit if direct measurement becomes nondeterministic, materially gameable, or
unable to classify a governed carrier without hidden exclusions. Retire this
record when the executable quality owner preserves the rejected alternatives,
semantic-review boundary, and revisit trigger without turning configuration into
a second architecture document.
