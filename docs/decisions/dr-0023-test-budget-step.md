---
subject: ethos:decision:test-budget-step
role: decision
state: canonical
decision_id: DR-0023
decision_status: accepted
relations:
  current_owner: ../../openspec/specs/quality/spec.md
---

# DR-0023: The Test Ceiling Moves to 105,000 for the beta.8 Work

Status: canonical rationale. The native source-budget declaration owns the number.

Date: 2026-11-11.

Purpose: preserve the necessity review that moved the test ceiling one 5,000 step, what was removed
first, and when to look again.

See also: [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md),
[DR-0019: The source budget counts code, not layout](dr-0019-layout-invariant-source-budget.md),
[DR-0020: The product ceiling moves to 80,000 for the RC work](dr-0020-product-budget-step.md) and
the `test-budget-step` OpenSpec Change.

## Context

After 0.2.0-beta.7 the tests measure 99,899 of their 100,000 line-equivalent ceiling, which
leaves 101. Two designed Changes for beta.8 add tests: the history rebuild, about 938 to 1,390
line-equivalents over its two landings and 360 to 520 in the first, and budget categories from
file roles, about 65 to 120. DR-0010 allows one 5,000 step only after the growing owner retires
proved duplication and superseded mechanics, and the owner's 2026-11-01 rule lets the agent take
that step with evidence.

## Decision

- **Removed first.** Measured on the enforced token measure, which layout does not move: the
  duplicated test behaviors gave each of 30 groups one owner and took the tests from 99,993 to
  99,854 (-139); one fixture signer owner removed 13 more (-21 effective lines); the operation
  catalog's conversion removed 12 (-227 effective lines); one fixture construction authority
  replaced three builders at no cost (+0).
- **What still needs the space.** The history rebuild's record, grammar, readiness and apply, which
  two adopters need to remove a private forge's identity from their published history, and the
  budget's role categories, which the fleet's package-identity design builds on.
- **Why not more removal now.** Fixture construction's remaining builder families (publication,
  lifecycle, proof and gates, budget) are estimated at 5 to 40 each, at most about 160 together,
  far short of the history rebuild's need. They continue as their own steps and each must hold its
  delta at or below 0.
- **The step.** The test ceiling moves one step, from 100,000 to 105,000 line-equivalents.

## Alternatives Rejected

- **Take the step inside the history rebuild:** it would put the budget decision in a feature
  Change and leave the role categories without space; one standalone step serves both.
- **Compress or relabel tests:** invalid repairs under the PDC and DR-0019.
- **Delete necessary tests:** the PDC treats removed necessary tests as an invalid repair.

## Consequences and Boundary

- The beta.8 consumers have about 5,100 line-equivalents of space against about 1,000 to 1,510
  planned.
- This record admits no growth by itself; each later step needs its own review.

## Evidence and Revisit

Measurements: the lanes' source-budget reports recorded in the `test-parallel-implementations`,
`fixture-signer-owner`, `catalog-groups` and `repository-spec` tasks, and this Change's own report
at its lane head. Revisit when both consumers land with more than 2,000 line-equivalents to spare,
so the ceiling can return toward the measured size, or when the tests reach 103,000.
