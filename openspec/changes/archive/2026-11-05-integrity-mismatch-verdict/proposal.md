# Proposal

## Why

The integrity provider reports every refusal as `unknown` with `source_integrity_unproven:<path>`,
including byte mismatches: a generated artifact that differs from what its native owner renders,
or an upstream member or received archive that differs from its pinned original. Those are
observed conflicts, not facts that ETHOS could not verify. Before `cause-preserving-results` a
proof forced every non-pass gate to `block`, which hid this. Now the proof reports the provider's
own class, so a drifted artifact made the proof `unknown`. The kernel's closed reduction says a
conflict is `block`, and only an unverifiable fact is `unknown`.

## What Changes

- The integrity provider reports a byte mismatch as `block` with its own code:
  `source_generated_bytes_mismatch:<path>`, `source_upstream_member_mismatch:<path>` or
  `source_upstream_archive_digest_mismatch:<path>`.
- Every other refusal, such as an artifact or archive that cannot be read or qualified, stays
  `unknown` with `source_integrity_unproven:<path>`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `quality`: the integrity provider separates a byte conflict from an unverifiable member.

## Impact

`src/ethos/adapters/gates/provenance/observation.py` and its tests. A drifted artifact's proof
moves from `unknown` back to `block`, now with the mismatch named.
