# Proposal

## Why

A full proof of a lane with 6,257 changed paths passes every gate and is refused when its record
is written: `attestation_member_too_large`. The record is 2,102,310 bytes, and an accepted
requirement bounds a member being added to the Attestation set at 1 MiB. A proof's record carries
its whole plan, and the plan names each changed path twice, about 253 bytes a path in that lane.
So the bound is passed by any lane with many changed paths: the reporting repository's first
record over 1 MiB is at about 1,220 changed paths. A landing's two records carry the proof by
value and pass the bound with it.

The owner moved this repair into 0.2.0-beta.12 on 2026-11-21.

## What Changes

- A proof record cites its plan by the plan's digest. The record takes the predicate
  `proof:execution-digest` and holds its artifact references and no plan. The plan's canonical
  bytes are written beside the proof's other artifacts, as `ethos/artifacts/<plan digest>.json`.
- Reading a cited record resolves the plan from that file and fails closed by name when the file
  is absent, when its bytes are not the cited digest, when a write would replace other bytes, and
  when the bytes are not a plan.
- A record written before this change (`proof:execution`, the plan by value) is read as before
  and touches no plan file.
- Retention keeps a plan file while a record cites it and deletes it only when the proof leaves.

The 1 MiB bound does not move.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The requirement on the Attestation set bounds a member and names no body shape for a proof,
and a cited record keeps a digest and its artifact references. No requirement changes, so
`skip_specs: true` applies.

## Impact

Proof issuance, validation and admission; the two records of a landing; the kinds retention
knows; three gap codes.

A released runtime reads the set and the landing's records. It does not admit a cited proof, so
it proves the head itself, and its own record then carries the plan by value. At the sizes this
repair exists for, that record is refused by the same bound: measured at 1,404 changed paths. A
rollback to an earlier release therefore leaves such a head unprovable there.

Each issuance of a cited record writes the plan file, about 1.2 MB at 1,404 changed paths. A
released runtime does not know the file's kind: it keeps the file and never reads or retires it.
