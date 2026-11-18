# Proposal

## Why

DR-0028 moved the test ceiling to 110,000 line-equivalents and named its own revisit: when the
tests reach 108,000. On 2026-11-19, at the head of the lane that follows 0.2.0-beta.11, the
source-budget gate reads 109,497 of 110,000 for the tests, and 503 are free.

Four first slices of gate rows are built and wait for that lane. Measured on their patches with
the budget tool on 2026-11-17 they need 1,476.5 line-equivalents of tests together: `gate-reuse`
449.3, `fast-tier` 181.0, `gate-environment` 150.0 and `store-retention` 696.3 in four slices. The
rows that are not built yet are not sized here.

A census of the lane's tests on 2026-11-19 read 559 files and 3,493 test functions for what four
mechanical ways could remove. It found no test whose body equals another's, no group of three or
more tests of one module that differ only in constants, no fixture that nothing requests, and
two helpers that nothing uses. A third helper that no test file names is called from code that the
tests hand to a child process as text, so it stays. Not measured: two tests that cover one
behavior in different words, which needs coverage by test.

DR-0010 allows one 5,000 step only after the growing owner retires proved duplication, and the
owner's rule of 2026-11-01 asks for the removal first. The owner decided on 2026-11-17 that the
ceiling takes one step, to 115,000.

## What Changes

- The two helpers that nothing uses are removed. The gate's reading falls from 109,497 to
  109,484. No test goes.
- DR-0033 records the review: what was removed first, what needs the space, why further removal
  does not close the gap now, and when to look again. It is written in the form of
  `decision-record-form`, it updates DR-0028, and DR-0028 carries the two marks.
- The test ceiling in `.config/checks/format-selection/policy.toml` moves one step, from 110,000
  to 115,000 line-equivalents.

Not breaking: the number is this repository's own declaration, and no governed repository reads
it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The native source-budget declaration owns the number, so `skip_specs: true` applies.

## Impact

`.config/checks/format-selection/policy.toml`, `docs/decisions/dr-0033-test-budget-step-115.md`,
`docs/decisions/dr-0028-test-budget-step-110.md`, `docs/decisions/README.md`, and two test
modules: the support module of the command runner and the tests of the hosted tool supply. The
Change stands alone and before the built slices, for the reason that DR-0028 gives against a step
inside a row: the other rows would be left without space.
