## Context

The target is a linked diverged successor at an expired lease with ten unique
dirty tracked paths and no staged patch. Accepted history subsequently
implemented, hardened, archived, and canonically fused its Task 4 semantics.

## Decision

Freeze the exact source observation and dirty patch digest. Promote a
current-base target-specific semantic judgment. Do not replay the historical
working tree: exact source-ELOC blobs are already accepted, taxonomy-byte and
replay-state semantics are present, and current byte-measurement APIs use
stricter closed signatures and ordered inventory binding.

After accepted closeout, use native preserve-retire to protect the exact source
payload before removing only the source branch and worktree. Keep package clear
as a later exact-manifest transition.

## Risk Controls

- Any owner, lease, Claim, process, opener, source head, dirty path, patch,
  Chronicle, accepted basis, or package drift blocks the effect.
- Valid-owner overlapping lanes remain observe-only.
- Native preservation precedes source removal.
- Package clear requires a separate accepted exact-manifest carrier.
- No raw Git deletion, force removal, remote mutation, or unrelated cleanup is
  authorized.
