# Proposal

## Why

Landing compares the proof's policy with a read-only `prove --full` plan of the installed runtime,
and bounds that probe by the tool deadline, 60 s. On 11-09 the plan took 60 s at host load 36 to 40,
so landing refused three times with `predecessor_policy_probe_timeout` while the proof and the
policy were sound, and waited about 80 minutes for the host to calm down.

## What Changes

- The predecessor policy probe is bounded by the gate deadline, the bound of one gate's run, instead
  of the tool deadline. A probe that exceeds it still refuses as `predecessor_policy_probe_timeout`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None.

## Impact

- `src/ethos/adapters/mutation/proof_admission.py` (`predecessor_policy_gaps`).
- `tests/unit/kernel/test_proof_admission.py`.
- A landing under host load waits for the plan instead of refusing it; the probe stays bounded.
