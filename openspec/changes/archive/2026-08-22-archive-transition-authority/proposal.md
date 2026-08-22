## Why

A completed Change can be archived and committed outside the ETHOS controller
while its Work Lane Lease still names the pre-archive HEAD and active carrier.
The repository then contains an exact valid archive post-image, but `prove`
misdirects the operator to adoption and rebind derivation treats the carrier
move as an ambiguous semantic Commitment replacement.

## What Changes

- Recognize one exact direct-child, byte-identical active-to-archive carrier
  relocation from Git facts.
- Route recovery through the existing `ethos lane archive-change` owner, which
  advances the Lease and records the terminal Attestation without replaying
  OpenSpec or creating another commit.
- Make proof and rebind derivation emit the same complete recovery command.
- Fail closed for wrong-parent, semantically changed, or ambiguous archive
  targets.
- Delete the duplicated archive-postimage classification from the recovery path
  by sharing one exact fact classifier.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `command-plane`: proof and rebind projections identify the existing exact
  archive recovery operation and expose its executable command.
- `repository-governance`: a committed exact archive post-image is classified
  and recovered through the same lifecycle-effect authority.

## Impact

- Archive recovery and Commitment-rebind derivation.
- Proof remediation and lane command projection.
- Focused archive, rebind, proof, and adversarial recovery tests.

Out of scope: adopter repository writes, accepted-ref/tag publication, lane
creation compensation, supply-chain upgrades, broad performance work, or a new
recovery ledger/state machine.
