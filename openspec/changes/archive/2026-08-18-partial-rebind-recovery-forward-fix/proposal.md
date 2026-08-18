## Why

`lane rebind-commitment` can persist its Git CAS, fail before the Lease CAS,
then fail compensation. With intent and evidence absent, retry misclassifies
the partial state and leaves the lane blocked.

## What Changes

- Recognize the exact state where the target ref is present while the Lease
  still matches the immutable receipt's old generation.
- Make dry-run project one deterministic recovery state and copyable retry.
- Make apply advance only the exact Lease generation and persist the terminal
  Commitment-rebind Attestation.
- Reconstruct missing plan-bound intent/evidence only from exact receipt, old
  Lease, target ref/tree, index, and overlay coordinates.
- Continue to reject colliding evidence or any ref, Lease, receipt, tree,
  index, overlay, or authority drift.

## Capabilities

### New Capabilities

None

### Modified Capabilities

- `repository-governance`: Commitment-rebind partial effects become publicly
  and exactly recoverable.

## Impact

The bounded change touches the existing Commitment-rebind transaction and its
focused tests. It adds no compatibility reader, parallel state store, wrapper,
or second authority.
