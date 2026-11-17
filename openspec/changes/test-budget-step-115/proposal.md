# Proposal

## Why

DR-0028 moved the test ceiling to 110,000 line-equivalents for the batch of 0.2.0-beta.12 and
named its own revisit: when the tests reach 108,000. At the head of that batch the source-budget
gate reads 108,935 of 110,000 for the tests, and 1,065 are free.

The first slices that are prepared for 0.2.0-beta.13 need more than that. One is measured on its
patch: the first slice of `fast-tier`, 181.0. The others are estimates of their design studies of
2026-11-17: `gate-environment` 120, `rollback-after-repair` 80 to 110, the first two slices of
`release-rehearsal` 250 to 410, `gate-reuse` 380, `store-retention` 230, `proof-output-scratch`
210 and `unsearchable-path-absence` at most 60. Together they are about 1,500 to 1,700, before the
batch's off-gate row and before `release-provenance`, which has no study yet.

A census of the batch's tests on 2026-11-17 read 557 files and 3,476 test functions for what four
mechanical ways could remove. It found no test whose body equals another's, no group of three or
more tests of one module that differ only in constants, no fixture that nothing requests, and
two helpers that nothing uses, 10 lines together. A third helper that no test file names is
called from code that the tests hand to a child process as text, so it stays. Not measured: two
tests that cover one behavior in different words, which needs coverage by test.

DR-0010 allows one 5,000 step only after the growing owner retires proved duplication, and the
owner's rule of 2026-11-01 asks for the removal first. The owner decided on 2026-11-17 that the
ceiling takes one step, to 115,000.

## What Changes

- The two helpers that nothing uses are removed, measured by the budget tool.
- A decision record preserves the review: what was removed first, what needs the space, why
  further removal does not close the gap now, and when to look again.
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

The format-selection policy, one decision record with its line in the index, and the two test
modules that hold those helpers. The Change stands alone and first in the batch of 0.2.0-beta.13, for
the reason that DR-0028 gives against a step inside a row: the other rows would be left without
space.

Owner: the release lead. Next action: the design, the tasks and the measured removal when the
batch lane of 0.2.0-beta.13 opens. Read again: at the cut of 2026-11-19.
