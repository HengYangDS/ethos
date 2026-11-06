# Proposal

## Why

The archived `proof-readiness` ran the readiness tier by passing its gate ids to the host gate
observation. That observation re-resolves the ids as a selection, and a selection must satisfy the
repository's quality obligations. The behavior obligation belongs to a test gate, which the
readiness tier excludes by definition. So the first real run on the lane refused at once with
`quality_obligation_unproven:behavior` and ran nothing. The unit test did not catch this, because it
replaced the policy resolution.

## What Changes

- The readiness run resolves the full plan once and runs the tier's nodes from that full policy
  with the existing gate graph runner. The full policy has no obligation gaps, so no selection is
  judged against obligations that the tier cannot meet.
- It still binds the exact head and execution source, still writes no attestation, and still names
  the remaining gates as not run.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement from `proof-readiness` is unchanged; this fixes its implementation, so
`skip_specs: true` applies.

## Impact

`src/ethos/surface/cli/proof/host.py` and its tests.
