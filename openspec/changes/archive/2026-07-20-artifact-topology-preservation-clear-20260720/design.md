## Context

`preserve-retire` correctly retained dirty source state before removing its
lane. Its durable decision and receipt are required audit evidence; the bundle
and patch are removable only when the exact manifest is verified and current
accepted truth proves that they add no unique behavior.

## Design

Use a fresh, owned, current-base Work Lane to carry one Claim, Chronicle, plan,
and OpenSpec delta. The Chronicle explicitly selects
`lane_resolution/clear-preservation` for one decision id and manifest. Native
clear rechecks that manifest, then removes the package and emits a clear receipt.
The earlier decision and receipt remain. The clearance carrier is then retired
through the ordinary landed lifecycle.

## Alternatives

- Retain the package indefinitely: rejected because its only patch is stale
  parity metadata and it would become unowned residue.
- Remove it manually: rejected because it bypasses manifest binding, durable
  clear receipt, and the irreversible control surface.
- Clear a batch of packages: rejected because no batch semantic proof exists.

## Proof Strategy

Validate strict OpenSpec and claims, compare the exact preserved patch with the
accepted parity record, refresh parity after the archive, run HEAD-bound
executed proof, locally land/closeout, perform native clear, verify the original
receipt and new clear receipt, then retire this carrier.
