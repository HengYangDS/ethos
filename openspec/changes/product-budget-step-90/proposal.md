# Proposal

## Why

DR-0025 moved the product ceiling to 85,000 line-equivalents and named its own revisit: when the
product reaches 83,000 before the 0.3.0 reductions. That point was passed without a review. On
2026-11-24, after the repair of the locked tool install landed, accepted `dev` read 84,888, with
112 free.

Three pieces of approved work wait for space: the first accepted branch of a repository adopted
from its release branch (84 line-equivalents, measured on its patch), the second half of the host
queue layer and the command of the known-defect carrier (neither built, neither sized here).

DR-0010 allows one 5,000 step only after the growing owner retires proved duplication, and the
owner's rule of 2026-11-01 asks for the removal first. On 2026-11-24 the owner decided the step
before that review was made, knowing that it had not been made. The review followed the same
day: a search of the whole product for top-level definitions that no tracked file names again
found one, and a search for structurally identical function bodies found none.

## What Changes

- The one unused definition is removed: the constant of a refusal code that nothing raises.
- DR-0036 records the decision, that it preceded its review, what the review found, and when to
  look again. It is written in the form of `decision-record-form`, it updates DR-0025, and DR-0025
  carries the two marks.
- The product ceiling in `.config/checks/format-selection/policy.toml` moves one step, from
  85,000 to 90,000 line-equivalents.

Not breaking: the number is this repository's own declaration, and no governed repository reads
it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The native source-budget declaration owns the number, so `skip_specs: true` applies.

## Impact

`.config/checks/format-selection/policy.toml`, `docs/decisions/dr-0036-product-budget-step-90.md`,
`docs/decisions/dr-0025-product-budget-step-85.md`, `docs/decisions/README.md` and
`src/ethos/contracts/semantic.py`. The Change stands alone and before the work that the space is
for, for the reason that DR-0028 gives against a step inside a row.
