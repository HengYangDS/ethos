---
subject: ethos:decision:test-budget-step-110
role: decision
state: canonical
decision_id: DR-0028
decision_status: accepted
date: 2026-11-15
relations:
  current_owner: ../../openspec/specs/quality/spec.md
  updates: DR-0023
  updated_by: DR-0033
---

# DR-0028: The Test Ceiling Moves to 110,000 for the beta.12 Work

Purpose: preserve the review that DR-0023's revisit point required, what was removed first, why the
test ceiling moved one more 5,000 step, and when to look again.

See also: [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md),
[DR-0019: The source budget counts code, not layout](dr-0019-layout-invariant-source-budget.md),
[DR-0023: The test ceiling moves to 105,000 for the beta.8 work](dr-0023-test-budget-step.md),
[DR-0029: The release candidate gate gains the law, and its dates become earliest
dates](dr-0029-release-candidate-gate-successor.md) and the `test-budget-step-110` OpenSpec Change.

## Context

DR-0023 asked for a review when the tests reach 103,000 line-equivalents. With the ten gate rows of
0.2.0-beta.11 landed, the tests measure 104,755 of 105,000, and 245 are free. DR-0029 orders this
step alone and first in the batch of 0.2.0-beta.12, with a measured removal, and that batch holds
nine gate rows. DR-0010 allows one 5,000 step only after the growing owner retires proved
duplication and superseded mechanics, and the owner's rule of 2026-11-01 lets the agent take that
step with evidence.

## Decision

- **Removed first.** Measured on the enforced token measure, on the landed tree. One passing graph
  run and one queue read replaced four copies in the host proof tests (-29.2). The exit table's
  copy of the short-write case, which the output tests own, went (-13.0). The rollback journey uses
  the shared tree writer and Git helper (-5.8), and a repeated declaration assertion went (-3.2).
  Together that is 51.1 line-equivalents, and the tests stand at 104,704 with 296 free.
- **Two prepared removals do not count.** Both were measured on 2026-11-14 on a prepared stack.
  One, 7.0 in the admission tests, no longer applies after three commits that landed, and the host
  row of this batch rewrites that module. The other, 24.8, removed a repeated test that only the
  first preparation of the adopter bump added. The bump as now prepared holds one table and one
  journey, so nothing is left to remove.
- **What still needs the space.** The nine rows of 0.2.0-beta.12. Three are prepared and measured:
  the host row's second Change at 351.9, the adopter bump at 204.7 and the hosted reader at 375.5.
  Together they are 932.1, more than three times the 296 that remain. The plan's estimates for
  the other six add up to 670. The ten sized Changes of 0.2.0-beta.11 measured 1,662 against 785
  estimated on their prepared stack, 2.1 times. At that factor the six need about 1,410 and the
  batch about 2,340.
- **Why not more removal now.** The search of 2026-11-14 over the batch's tests found four pairs
  of functions with the same or nearly the same shape. Two went in that preparation, and two
  assert distinct obligations. Two further candidates each drop a scenario that its Change names:
  the enforced exit case (18.4) and the close of a receipt through hook activation (9.7). A builder
  for the pinned repair fixture measured 0.4 and is not taken. The larger reduction stays
  structural, as DR-0019 found: a Git port with an in-memory adapter that replaces patch-based
  tests, which is 0.3.0 work.
- **The step.** The test ceiling moves one step, from 105,000 to 110,000 line-equivalents. (Replaced
  by [DR-0033](dr-0033-test-budget-step-115.md).)

## Alternatives Rejected

- **Merge same-shape tests, or drop the enforced exit case:** each asserts a distinct named
  obligation, the exit case is a scenario of its Change's specification delta, and DR-0010 rejected
  the same merge twice.
- **Move rows of 0.2.0-beta.12 to a later batch:** every row is a gate row that DR-0029 keeps, and
  each of the next two batches already holds nine.
- **Compress or relabel tests:** invalid repairs under the product design contract and DR-0019.
- **Two steps at once:** DR-0010 allows one reviewed step at a time.
- **Take the step inside a row of the batch:** it would put the budget decision in one row and
  leave the other eight without space.

## Consequences and Boundary

- 0.2.0-beta.12 has 5,296 line-equivalents of space against about 2,340 expected, of which 932.1
  are measured and the rest is estimated.
- The step is not expected to hold the whole release candidate: 24 rows follow this batch. The
  review below decides the next step; this record does not.
- This record admits no growth by itself. Each later step needs its own review and a measured
  removal.

## Evidence and Revisit

Measurements: the ceiling reading of the landed tree and of this Change's tree, the budget tool's
delta for each of the four test modules, and the preparation reports of the three measured rows, as
the `test-budget-step-110` tasks record them at the lane head. Revisit when the tests reach 108,000,
when 0.2.0-beta.12 is tagged, or when the 0.3.0 reduction lands, whichever comes first. (Replaced by
[DR-0033](dr-0033-test-budget-step-115.md).)
