# Proposal

## Why

Nothing retires the records that proofs, merges and lane retirements write to the Git-common store,
so it grows for as long as a clone lives. On 2026-11-08 ETHOS's own store held 16 GiB: lane
retirement requests 3.4 GiB and receipts 3.0 GiB, artifacts 2.1 GiB, beside custody, runtimes and
tool caches that keep their own owners. Store retention (the archived `rc-plan`, Appendix D) retires
old records through one allowlisted write-ahead plan; this Change adds the plan's read-only preview
and the parameters it reads, and the apply that deletes follows as its own Change.

## What Changes

- `ethos hook retire-records` previews retirement. Only the runtime that `runtime/CURRENT` selects
  runs it; it reads its age floors from the accepted branch's binding; it refuses while a proof
  holds the repository's proof slot.
- The preview classifies the allowlisted kinds by their writers' exact schemas: proof-check
  documents, merge preimages, native and JavaScript attempt archives, and lane retirement units that
  are terminal, receipt-only or manifest-only. Anything else under the store is reported by path and
  bytes and kept.
- An item is kept when a live Attestation member, a kept store file, a reached item or the accepted
  tree names its digest, read through zip, gzip, tar and base64 content within declared bounds; a
  kept carrier that cannot be read within them refuses the preview.
- An unnamed item older than its floor is a candidate; the preview writes the plan, with the frozen
  cutoffs and each item's kind, path, size, mtime and state, before any later deletion can read it.
- The paradigm gains a `retention` group: the floors `grace_seconds` and `record_seconds`, which a
  repository may raise without a reason but not lower, and the bounds `decode_depth`,
  `decode_bytes` and `status_bytes`.
- Writing content identical to an existing content-addressed file refreshes its mtime, so a record
  that a writer adopts again starts its floor again.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: store records retire only through an allowlisted write-ahead plan; this
  Change adds the preview's scenarios.
- `repository-paradigm`: a floor row applies a higher value without a reason and treats a lower one
  as a gap.

## Impact

- New `src/ethos/application/retention.py` and `src/ethos/adapters/store/retention/`; the
  `hook retire-records` command in `src/ethos/surface/cli/hook/commands.py`.
- `src/ethos/contracts/paradigm/declaration.py` and `paradigm.toml`,
  `src/ethos/repository/paradigm/parameters.py` and `src/ethos/adapters/store/content_addressed.py`.
- Tests under `tests/unit/adapters/store/` and `tests/unit/repository/`.
- Publication requests and superseded lane retirement units join with the apply Change.
