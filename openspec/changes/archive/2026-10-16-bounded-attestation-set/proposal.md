## Why

The selected Attestation set holds 3,253 members and 560 MiB, and no member ever leaves: every
update is the union of the observed set and new members. About 413 MiB are evidence files embedded
since 2026-10-12 in 35 open-predicate members that no product reader consumes, because ETHOS has no
custody carrier that can release bytes. Routine proof, ref-update and publication records outlive
the lanes and heads they served. Every land, closeout, publish, retire and release reads and
validates the whole set, so its cost grows with history, and full proofs time out in tests that read
the real set.

## What Changes

- **BREAKING** An Attestation member carries a claim, not files: canonical bytes above 1 MiB fail
  closed before any effect.
- Evidence bytes move to a Git-common, content-addressed custody store that is never tracked or
  published. A member binds each file as `custody:sha256:<digest>`, and
  `ethos attestation record --evidence` stores and binds the declared files.
- **BREAKING** Every member has one lifetime derived from its existing bindings. A set update
  removes the members whose lifetime ended by positive evidence: a superseded head that no ref,
  peeled tag, worktree or peer's latest publication selects, an expired validity window, a repair
  whose pre-repair objects are gone, or an explicit release. Lane records, release tags, accepted
  release identities and the starter formation stay, because current readers still select them.
- New `ethos attestation release` removes one open-predicate member at the request of its verifier
  or of a reviewed owner, and deletes custody bytes that no remaining member binds.
- Existing custody members migrate only after their owners decide. Each file moves byte-exact and is
  verified against its embedded digest before the original is released.
- The temporary in-process member reuse (proof-throughput 2.15) is removed once reads are bounded;
  file-backed native output capture stays.

Out of scope: lifetimes for lane records, which need consumer-indexed evidence (archive intent
through proof commitments, refresh provenance through peer proposal retirement); deduplicating
copies inside live routine records; an archive of ended members; a predicate index; and other
carriers. Git history, Forge CI and release records keep the history that ended members no longer
hold.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `adapters`: the set carrier removes ended members within its exact-CAS update, bounds member size
  and keeps evidence bytes in released local custody.
- `command-plane`: record binds custody evidence and refuses oversized members; release removes one
  open-predicate member.
- `repository-governance`: each Attestation has a lifetime that ends with the transition that
  consumes it.

## Impact

The Attestation set adapter, its lifetime owner, the custody store, the `attestation` commands,
every reader journey that selects historical members (land, closeout, publish, retire, release
catch-up, signature repair, starter evolution) and the product design contract's Attestation and
historical-bytes statements. Routing remains the repository-governance owner. Foreign custody
members change only through their owners' decisions. Adopters receive the behavior through their
selected runtime; that installation is a separate decision.
