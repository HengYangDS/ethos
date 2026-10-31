# Proposal

## Why

npm audit names the vulnerable dependencies through which each affected package is reached in its
`via` list, and a peer dependency makes that graph cyclic. ESLint depends on
`@eslint-community/eslint-utils`, which declares ESLint as a peer, so an advisory anywhere under
ESLint lists each of the two in the other's `via`. The dependency audit refuses every cycle with
`cyclic npm aggregate references`, so its decision becomes `finding_identity_unavailable` instead of
naming the advisory. On 2026-10-31 GHSA-g3hv-75wg-m249 in minimatch reached ESLint's tree, and the
release audit of `dev` reported an unknown decision instead of the fixable minimatch finding. Every
governed repository that locks ESLint meets the same refusal.

## What Changes

- Each npm aggregate resolves to every advisory reachable through its `via` references, through
  cycles as well.
- An aggregate from which no advisory is reachable, a dangling reference and every other unbound
  identity still leave the finding identity unavailable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The quality specification already requires the audit to resolve every aggregate reference to
its concrete advisory roots and exempts no cycle, so `skip_specs: true` applies.

## Impact

`src/ethos/repository/policy/quality/dependency_acceptance.py` and its tests. Native audit output,
counts and exit status are unchanged; only the identity resolution of cyclic reports changes.
