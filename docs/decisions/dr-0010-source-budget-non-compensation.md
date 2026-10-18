---
subject: ethos:decision:source-budget-non-compensation
role: decision
state: canonical
decision_id: DR-0010
decision_status: accepted
relations:
  current_owner: ../../.config/checks/format-selection/policy.toml
---

# DR-0010: Source Budget Non-Compensation

Status: canonical rationale. Executable thresholds are owned by quality
configuration.

Date: 2026-09-02 (record established); revised 2026-09-08.

Purpose: preserve why unrelated source classes cannot compensate for one
another and why size remains a tripwire rather than a design target.

See also: [Documentation Root](../README.md),
[Terminal Governance Product Design](../plans/terminal-governance-product-design.md),
and `.config/checks/format-selection/policy.toml`.

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

Measure owned source deterministically by carrier and Python role, enforce the
explicitly declared ceilings, and cross-check measurements independently.
Python product and test ceilings are required and independent. Other categories
and the heterogeneous global total remain observations unless explicitly bounded;
the September 8 user decision removes the previous mandatory aggregate ceiling.
Structural duplication, competing owners, and semantic overlap decide deletion;
line count alone does not.

Budgets are non-compensating: a surplus in tests, documentation, or one source
role cannot pay for excess in another. Per-file limits remain readability
tripwires. A breach triggers semantic review—delete, absorb, rename, or split by
real ownership—not mechanical file fragmentation.

## Alternatives Rejected

- **One aggregate repository budget:** rejected because unrelated domains can
  subsidize one another and obscure the source of growth.
- **Raw LOC as semantic currency:** rejected because formatting, literals, and
  carrier movement can game it.
- **A private metric vector runtime:** rejected because its parser, replay,
  shadow, debt, and migration machinery exceeded the invariant it protected.
- **Splitting solely to satisfy a threshold:** rejected because it preserves the
  same mixed ownership under more physical entities.

## Consequences and Boundary

- Every governed carrier must be classified into one measured owner or fail
  closed; hidden exclusions cannot make a budget green.
- Budget changes require evidence at the owner that grows and cannot be justified
  by unrelated repository shrinkage.
- Direct native measurement and independent cross-checks are preferred over a
  custom metric runtime.
- Passing a size gate never proves architectural quality; semantic ownership and
  behavior-preserving tests remain authoritative.
- Generated outputs and archived OpenSpec remain separately visible, not charged
  to maintained source. Handwritten generators, active intent, tests, and docs
  remain measured; moving live authority into an excluded class is not deletion.

## Evidence and Revisit

- `.config/checks/format-selection/policy.toml` owns current classifications,
  thresholds, native commands, and the independent `scc` cross-check.
- `src/ethos/domain/source_budget/measurement.py` executes deterministic
  measurement; `src/ethos/repository/policy/quality/measurement.py` owns the
  validated declaration shared by budget and carrier-format consumers.
- `tests/unit/domain/source_budget/` covers non-compensation, classification,
  deterministic output and public observation.
- `tests/architecture/test_format_selection.py` and the native import-linter
  contract verify shared carrier ownership without an adapter-to-domain dependency.
- [Module Layout And Visibility Rules](../../rules/module-layout.md) prevents
  size thresholds from authorizing suffix-flat or metric-driven splits.

Revisit if direct measurement becomes nondeterministic, materially gameable, or
unable to classify a governed carrier without hidden exclusions. Retire this
record when the executable quality owner preserves the rejected alternatives,
semantic-review boundary, and revisit trigger without turning configuration into
a second architecture document.
