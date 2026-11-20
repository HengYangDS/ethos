# Proposal

## Why

The owner directed on 2026-11-18 that every governed repository is optimised for performance and
that iteration gets faster. Every full proof on a host that declares a load limit waits about
fifteen seconds between its readiness gates and its first test or package gate, whatever the
host's load. Four proofs of one governed repository show 15.1 or 15.2 seconds, and ETHOS's own
proof of the release head shows 15.3.

The cause is the admission rule of 2026-11-04: two consecutive calm samples of the 1-minute load,
one sampling interval apart, so that one lull between busy phases is not taken for room. The
first sample is taken when the readiness gates have ended, so a proof on a quiet host with free
slots sleeps one interval for the second. For a repository whose proof is half a minute of
gates, that sleep is a large part of it.

## What Changes

- The proof reads the host's load once before its readiness gates and hands that sample to its
  admission. A sample within the limit that is at least one sampling interval old counts as the
  first of the two, when the proof takes both slots without waiting.
- Nothing else of the rule changes: a wait for a slot, a busy sample at admission, an earlier
  sample that was busy, missing or too young each leave the proof waiting for two fresh samples.

Not breaking: no proof is admitted on fewer than two calm samples one interval apart. A host
without a declared load limit did not wait and does not wait.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: a new requirement, "A load sample from before the readiness gates counts once",
  with two scenarios. It stands beside "Full proofs and nested work share the host admission",
  whose text is at the specification's bound of 500 characters and keeps every word: the two
  samples stay consecutive, and the new requirement says when the first of them may be older.

## Impact

`src/ethos/adapters/gates/proof_slot.py`, `src/ethos/application/proof/operation.py` and their
tests. The host's keeper is told before it lands: the rule that the host's prose rules rest on
keeps its two samples.
