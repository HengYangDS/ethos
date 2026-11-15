# Proposal

## Why

DR-0023 asked for a review of the test ceiling when the tests reach 103,000 line-equivalents.
DR-0029 orders the step that follows it alone and first in the batch of 0.2.0-beta.12, with a
measured removal. The archived `rc-scope-plan` design, decision 6, placed the review in the batch
before.

With the ten gate rows of 0.2.0-beta.11 landed, the tests measure 104,755 of 105,000 and 245 are
free. Four removals that were prepared on 2026-11-14 still apply to the landed tree and are worth
51.1. Two more no longer count. The first three prepared rows of 0.2.0-beta.12 measure 932.1
together, and six rows follow them. DR-0010 allows one 5,000 step only after the growing owner
retires proved duplication, and the owner's rule of 2026-11-01 lets the agent take that step with
evidence.

## What Changes

- Four test modules lose duplicated scaffolds and two repeated cases, 51.1 line-equivalents. No
  named scenario goes.
- DR-0028 records the review: what was removed first, what still needs the space, why further
  removal does not close the gap now, and when to look again.
- The test ceiling in `.config/checks/format-selection/policy.toml` moves one step, from 105,000 to
  110,000 line-equivalents.

Not breaking: the number is this repository's own declaration, and no governed repository reads
it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The native source-budget declaration owns the number, so `skip_specs: true` applies.

## Impact

`.config/checks/format-selection/policy.toml`, `docs/decisions/dr-0028-test-budget-step-110.md`,
`docs/decisions/README.md`, and four test modules: the host proof tests, the host command tests,
the exit table tests and the rollback journey.
