---
subject: ethos:decision:test-budget-step-115
role: decision
state: canonical
decision_id: DR-0033
decision_status: accepted
date: 2026-11-17
relations:
  current_owner: ../../openspec/specs/quality/spec.md
  updates: DR-0028
---

# DR-0033: The Test Ceiling Moves to 115,000 for the Built Slices That Wait

Purpose: preserve the review that DR-0028's revisit point required, what was removed first, why the
test ceiling moved one more 5,000 step, and when to look again.

See also: [DR-0010: Source-budget non-compensation](dr-0010-source-budget-non-compensation.md),
[DR-0019: The source budget counts code, not layout](dr-0019-layout-invariant-source-budget.md),
[DR-0028: The test ceiling moves to 110,000 for the beta.12 work](dr-0028-test-budget-step-110.md),
whose step and whose revisit point this record replaces, and the `test-budget-step-115` OpenSpec
Change.

## Context

DR-0028 asked for a review when the tests reach 108,000 line-equivalents. On 2026-11-19, at the
head of the lane that follows 0.2.0-beta.11, the source-budget gate reads 109,497 of 110,000 for the
tests, and 503 are free. Four first slices of gate rows are built and wait for that lane; measured
on their patches they need 1,476.5 together. DR-0010 allows one 5,000 step only after the growing
owner retires proved duplication and superseded mechanics, and the owner's rule of 2026-11-01 asks
for that removal first. The owner decided on 2026-11-17 that the ceiling takes this step.

## Decision

- **Removed first.** Two helper functions that no test and no tool uses went: `_externalized` in
  the support module of the command runner and `_serve_mise` in the tests of the hosted tool
  supply. The budget tool measured them at 4.0 and 8.9 line-equivalents on 2026-11-17. With them
  gone the gate reads 109,484, and 516 are free.
- **What the search found.** A census of the tests at that head read 559 files and 3,493 test
  functions. It found no test whose body equals another's, no group of three or more tests of one
  module that differ only in constants, and no fixture that nothing requests. A third helper that
  no test file names is called from code that the tests hand to a child process as text, so it
  stays.
- **What still needs the space.** Four first slices were measured on their built patches with the
  budget tool on 2026-11-17: the gate input key and its record at 449.3, the fast tier's report at
  181.0, the gate environment's report at 150.0, and the store's retention in four slices at 696.3
  (147.2, 292.8, 137.2 and 119.1). Together that is 1,476.5 against the 516 that remain. Each is
  measured again when it enters the lane. The rows that are not built yet are not sized here.
- **Why not more removal now.** The census covered the four mechanical ways and left these two
  helpers. Two tests that cover one behavior in different words were not measured: that needs
  coverage by test from one run of the whole suite. The larger reduction stays structural, as
  DR-0019 and DR-0028 found: a Git port with an in-memory adapter that replaces patch-based tests,
  which is 0.3.0 work.
- **The step.** The test ceiling moves one step, from 110,000 to 115,000 line-equivalents.

## Alternatives Rejected

- **Hold the built slices for a later batch:** each is the part of a gate row that its study found
  able to land, and it is built. Each later batch holds its own rows.
- **Read coverage by test before the step:** it needs one run of the whole suite under the host
  queue and then a removal one behavior at a time, while the slices wait. It stays the input of
  the next review.
- **Compress or relabel tests:** invalid repairs under the product design contract and DR-0019.
- **Two steps at once:** DR-0010 allows one reviewed step at a time.
- **Take the step inside a row of the batch:** it would put the budget decision in one row and
  leave the others without space, as DR-0028 found.

## Consequences and Boundary

- The tests have 5,516 line-equivalents of space against 1,476.5 measured for the four built
  slices. What the rows that are not built need is not measured.
- The step is not expected to hold the whole release candidate: the remainders of these rows and
  the rows of the later batches follow.
- This record admits no growth by itself. Each later step needs its own review and a measured
  removal.
- Of DR-0028, this record replaces the step and the revisit point. Its review, its rejected
  alternatives and its other consequences stand as written.

## Evidence and Revisit

The repository's owner decided the step on 2026-11-17, on the measured proposal of the session
that builds the product; that session reviewed the figures again at the lane head on 2026-11-19.
Measurements: the gate's reading at that head before and after the removal, the census of the
tests, and the preparation reports of the four built slices, as the `test-budget-step-115` tasks
record them. Revisit when the tests reach 113,000, when the next beta after 0.2.0-beta.11 is
tagged, or when the 0.3.0 reduction lands, whichever comes first. That review reads coverage by
test.
