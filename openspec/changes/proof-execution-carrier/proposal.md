## Why

A Work Lane can have an exact, reviewed archive staged while its committed HEAD
still needs fresh proof under a changed quality policy. The current proof command
requires that lane's working tree and index to equal HEAD, so its only apparent
workaround is to disturb the staged result or prove from another lane. Neither
preserves the original authoring authority and exact effect.

## What Changes

- Let an authorized proof request name a separate, clean Git worktree as its
  execution carrier while retaining the original lane's HEAD, actor, Lease,
  accepted intent, policy, Attestation store and archive effect.
- Validate the carrier's common Git directory, detached exact HEAD/tree and
  clean source before and after gate execution. Recheck the authoring lane's
  staged and working content, HEAD and Lease before issuing proof.
- Execute the current required gates, not replay or re-sign earlier checks.
  Reject foreign, dirty, stale or drifting carriers without modifying the
  staged archive.
- Keep the ordinary clean-lane proof path unchanged; do not add a second
  lifecycle, policy source or persistent carrier identity.
- Apply the user's conditional product ELOC capacity only in the native source
  budget after deletion review; preserve the independent test, per-file,
  coverage and required-gate floors.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: separate proof execution location from authoring
  authority without weakening exact-source and current-policy admission.

## Impact

The existing proof CLI, current-resolution compiler, source observer, gate
runner and Attestation issuance boundary, plus native positive and adverse
tests. A caller-selected carrier is an explicit execution resource, not an
authority or an archived copy of intent. No adopter repository is modified by
this Change. The accepted product count was 49,898/50,000 ELOC; the necessary
carrier boundary exceeds the remaining 102 ELOC after targeted simplification.
