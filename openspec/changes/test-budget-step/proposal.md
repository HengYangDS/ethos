# Proposal

## Why

The tests measure 99,899 of their 100,000 line-equivalent ceiling at `eeee0c2d8` (0.2.0-beta.7).
Two designed Changes for beta.8 add tests: `history-rebuild-map` about 938 to 1,390 line-equivalents
over its two landings (360 to 520 in the first), and `source-budget-roles` about 65 to 120. DR-0010
allows one 5,000 step only after the growing owner retires proved duplication, and the owner's
2026-11-01 rule lets the agent take that step with evidence.

## What Changes

- DR-0023 records the necessity review: what was removed first, what still needs the space, why
  further removal does not close the gap now, and when to look again.
- The test ceiling in `.config/checks/format-selection/policy.toml` moves one step, from 100,000 to
  105,000 line-equivalents.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The numeric limit is owned by the native source-budget declaration, so `skip_specs: true`
applies.

## Impact

`.config/checks/format-selection/policy.toml`, `docs/decisions/dr-0023-test-budget-step.md` and
`docs/decisions/README.md`.
