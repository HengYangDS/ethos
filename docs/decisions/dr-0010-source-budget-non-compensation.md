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

Date: 2026-09-02 (record established); revised 2026-10-18.

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

An enforced aggregate ELOC ceiling may increase by exactly 5,000 in one reviewed
step only when further meaningful simplification cannot preserve the necessary
complexity. The growing owner must first retire proved duplication and
superseded mechanics, reject zero-benefit abstractions, and identify the
remaining behavior or acceptance boundaries that require the space. This is a
source-policy change, never automatic growth admission or evidence that the
repository is globally minimal. Each later step requires a fresh necessity
judgment. Independent role accounting, the 512-ELOC per-file limit, measurement,
coverage and all other quality obligations remain unchanged.

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
  by unrelated repository shrinkage. A qualified increase uses one 5,000-ELOC
  step in the existing numeric owner; no parallel exception registry is needed.
- Test necessity is judged by distinct observable obligations, not test count or
  physical lines removed. Runtime-selection freshness, formatter effect fences
  and merge-task authority remain distinct acceptance boundaries.
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
  measurement; `src/ethos/repository/policy/quality/source_budget.py` owns the
  typed policy and native declaration parser shared by budget and carrier-format
  consumers.
- `tests/unit/domain/source_budget/` covers non-compensation, classification,
  exact boundaries, deterministic output and public observation; remeasurement
  uses the same gate.
- `tests/architecture/test_format_selection.py` and the native import-linter
  contract verify shared carrier ownership without an adapter-to-domain dependency.
- The October 18 necessity review retained duplicated-test retirement
  `a84bf1bce` (192 ELOC removed), rejected a zero-saving fixture abstraction,
  and checked the remaining owner-specific tests at source `17a52bec5`.
  Structural relocation `efc63f685` removed physical lines but increased test
  ELOC by 343; it is not budget compression evidence.
- [Module Layout And Visibility Rules](../../rules/module-layout.md) prevents
  size thresholds from authorizing suffix-flat or metric-driven splits.

Revisit if direct measurement becomes nondeterministic, materially gameable, or
unable to classify a governed carrier without hidden exclusions. Retire this
record when the executable quality owner preserves the rejected alternatives,
semantic-review boundary, and revisit trigger without turning configuration into
a second architecture document.
