## Why

A reviewed historical lane can have no remaining semantic obligation while its
staged, unstaged or untracked bytes still block every public retirement path.
Requiring another preservation copy does not discharge that obligation. The
existing abandonment operation already owns exact retirement receipts and
recovery; it must represent an explicitly reviewed content preimage as well as
a clean divergent history.

## What Changes

- Extend existing receipt-bound abandonment to reviewed content on a selected
  non-protected topic, including already-absorbed history.
- Bind the real root, index and complete no-follow filesystem inventory,
  including ignored resources, to the existing immutable operation.
- Recheck actor, Lease, accepted/ref coordinates and the content preimage before
  removal; preserve unknown, changed, locked or actively consumed resources.
- Reuse native worktree removal and existing monotonic recovery. Do not copy
  source into another archive or claim machine-proven semantic equivalence.

## Capabilities

### Modified Capabilities

- `repository-governance`: exact reviewed-content retirement through the
  existing abandonment and recovery commands.

## Impact

Retirement contracts, existing abandonment/operation and worktree effects,
content observation, CLI and regression tests. No new lifecycle command, task
registry, source backup, persistent snapshot database or adopter change.
Supply upgrades, broad directory reorganization and unrelated CI repairs are
outside this Change.
