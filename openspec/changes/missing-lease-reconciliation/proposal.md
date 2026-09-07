## Why

A registered Work Lane can retain valuable staged and unstaged work after its
local Lease disappears. Current start, resume, and takeover commands cannot
establish coordination for that state. Requiring a new lane or reconstructing
an obsolete Lease prevents the existing content from converging safely.

## What Changes

- Expose missing-Lease reacquisition through the existing Lease command owner.
- Bind explicit authorization to the exact branch, HEAD, index, working content,
  actor, and absent Lease; preserve Git and filesystem content unchanged.
- Reuse the existing four-field Lease storage and native effect Attestation.
- Report a concrete next command from missing-Lease diagnostics without
  suggesting lane creation or implying that coordination authorizes edits.
- Preserve the remaining distribution-allowlist regression from the historical
  source-policy lane and update the existing terminal route's dispositions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: missing local coordination can be reacquired without
  altering or recreating the retained Work Lane.

## Impact

The existing Lease lifecycle, command transport, coordination diagnostics, and
their tests change. No new persistent schema, carrier, registry, tool dependency,
or adopter-specific implementation is introduced.

Out of scope: overwriting live or expired foreign Leases, replaying divergent
commits, deleting dirty overlays, retargeting non-Work branches, and unregistered
worktree reconstruction. Those require their own existing authority boundaries.
