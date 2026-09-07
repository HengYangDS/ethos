## Why

The required Python coverage floor was lowered from 95 to 93, while tests only
checked that execution repeated the configured value. Default proof and local
CI also omit the floor, allowing internally consistent green results that do
not satisfy the repository requirement.

## What Changes

- Restore the existing coverage policy to a hard floor of at least 95 percent;
  delete the unused aspirational field and misleading requirement/evidence split.
- Make default proof, full proof, and local CI enforce the same current-HEAD
  line-and-branch measurement through the existing coverage owner.
- Replace the self-referential gate assertion with executed boundary cases.
- Cover missing behavior in current authority and lifecycle owners, consolidate
  redundant fixtures, and preserve all existing source and resource budgets.
- Correct the existing contract, terminal route, config guide, and quality skill
  projection without rewriting historical results or archived Changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the required coverage floor constrains every repository proof and
  cannot be reduced or bypassed to accommodate the measured result.

## Impact

The existing coverage policy, test gate, proof-set registry, local CI owner,
tests, and their documentation projections change. No new registry, workflow
state, policy carrier, dependency, lane, or adopter implementation is introduced.

Out of scope: supply upgrades, foreign-lane edits, hosted-runner topology repair,
new runtime activation, publication, and claims of global completion. Acceptance
of the preceding missing-Lease atom remains held until this floor is satisfied.
