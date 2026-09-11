## Why

The transferred signature-repair lane contains a necessary public recovery
capability that is not accepted. Its same-payload prerequisite also has a live
counterexample: the current comparator removes carriage returns from preserved
commit headers and can equate different unsigned payloads.

## What Changes

- Preserve every non-signature payload byte through the existing Git object
  observer, including headers, ordered parents, identities and message bytes.
- Compose one explicitly authorized, exact accepted-tip signature repair from
  the current signing, policy, ref-effect, worktree and Attestation owners.
- Re-observe signer trust, selected refs and clean linked worktrees before each
  effect; recover unknown or partial outcomes without repeating completed effects.
- Absorb the transferred lane's valid obligations and counterexamples, not its
  command-private request/progress stores or fixed candidate/dev/main selection.
- Keep object creation explicit: no command that creates a signed Git object is
  described as read-only. Proof, runtime activation and publication remain separate.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `command-plane`: one public accepted-tip repair and exact recovery continuation.
- `repository-governance`: byte-preserving signature replacement, current trust,
  selected-ref CAS, worktree safety and independently verified source absorption.

## Impact

Existing Git object/signing, accepted transition, ref admission and effect
recovery owners; thin CLI projection; isolated native Git and package acceptance
tests. No adopter source, remote effect, full-history rewrite, new persistent
semantic root, second operation store, compatibility alias or extra worktree.
