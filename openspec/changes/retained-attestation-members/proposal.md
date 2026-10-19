## Why

After bounded-attestation-set, the selected Attestation set still holds about 186 MiB, and a fresh
process needs 2.7 s to read it, so the temporary in-process member reuse stays. Twenty-four legacy
evidence members wait on their owners' decisions, 1,042 lane records never end because readers
still resolve retired lanes through them, and three set-writer gaps remain.

## What Changes

- Each custody owner decides through its own thread whether to release or migrate its members. A
  migrated file moves byte-exact into custody behind a bounded successor, and the owner accepts the
  preserved copy before the original is released.
- A retired lane's records end once neither proof admission nor proposal retirement can still
  select them. A reader whose facts cannot be observed keeps them.
- A lane's attested retirement closes its start like an exact inverse does, so the same name can
  start again at the same head instead of being refused as a content mismatch.
- A superseded head's acceptance record stays as lineage provenance for historical maintenance
  bases; its proof, integration and publication records still end with the head.
- Every set writer reports lifetime and custody gaps to its caller. An update that exhausts its
  retries deletes the custody bytes it stored that no selected member binds. A replay of a member
  already in the set reports it unchanged instead of applying the size bound.
- The in-process member reuse is removed once a fresh process reads the selected set in under 2 s;
  file-backed native output capture stays.

Out of scope: changes to the custody store, deduplication inside routine records, an archive of
ended members and a predicate index.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: custody bytes stored by a failed update do not outlive it.
- `command-plane`: record reports an existing oversized member as unchanged.
- `repository-governance`: a retired lane's records end with their last reader.
- `repository-transaction`: any attested reversal of an effect's refs closes that effect.

## Impact

The Attestation set writer and lifetime owner, the readers that select retired lanes' records
(proof admission's archived intent and proposal retirement's refresh provenance), the `attestation
record` command, the in-process member reuse, and the custody owners' Codex threads. Routing
remains the repository-governance owner. Foreign custody members change only through their owners'
decisions. An adopter receives the behavior through its selected runtime; that installation is a
separate decision.
