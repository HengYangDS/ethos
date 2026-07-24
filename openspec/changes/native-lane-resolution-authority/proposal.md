## Why

Clean ownerless Work Lane retirement currently treats a host-side verifier and
mixed historical record roots as part of ETHOS authority. That violates the
product boundary: ETHOS must own its Work Lane observations, admission,
coordination, effects, records, and recovery without depending on an unrelated
control plane.

## What Changes

- **BREAKING** Remove the mandatory external verifier, its process adapter, its
  response contract, provider-prefixed receipt fields, and compatibility tests.
- Make the effect executor perform one ETHOS-native admission from the immutable
  decision, Chronicle, Git worktree registration, configured branch-role policy,
  local lease/Claim state, accepted ancestry, and a fence-held re-observation.
- Cut current record authority to one new versioned root. Leave all predecessor
  records in place as immutable history; current decide/apply/recovery/receipt/
  clear/inventory paths do not fall back to them.
- Make receipt, reservation, and clear-record versions explicit and provider
  neutral. Preserve the existing fence, durable recovery, no-force worktree
  removal, accepted-ref verification, target-ref exact delete CAS, and
  postcondition-before-receipt invariants.
- Repair inventory so decision-only records and invalid current payloads are
  visible and blocking instead of silently omitted.
- Make native admission derive Work Lane role from the existing configured
  branch policy, including a non-default Work Lane branch prefix.
- Extend generic coupling governance so an undeclared external executable cannot
  silently become mandatory lifecycle authority.
- Keep the predecessor Claim active while the new Claim authorizes
  implementation; supersede it only after the native replacement has
  implementation, full proof, and official archive evidence. Normalize retired
  provider vocabulary from the current tracked tree while preserving chronology
  and meaning.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: subject=native-lane-resolution-authority;
  reuse=extend; change=modify; facet:lifecycle=retirement,recovery;
  facet:surface=contract,state,record,inventory,test,openspec,schema,docs;
  facet:authority=source,test,schema,openspec,evidence,claim.

## Impact

- Contracts and schemas for lane-resolution receipts, reservations, and clear
  records.
- Ownerless resolution admission/effect/recovery, record roots, inventory,
  state fencing, and CLI projection.
- Canonical repository-governance requirements, command reference, design and
  implementation plans, Claims, Chronicle, and parity evidence.
- The current tracked tree no longer contains or depends on the retired
  provider. Historical local records and Git history are not rewritten.

## Out Of Scope

- Moving, copying, deleting, re-signing, or reinterpreting predecessor local
  records.
- Rewriting Git history or editing archived session metadata.
- Retiring any real foreign Work Lane during implementation acceptance.
- Removing optional, explicitly configured semantic-attestation or policy
  adapters that are unrelated to lane-resolution effect authority.
- Renaming workspace policy keys or changing Work Lane creation semantics; this
  Change only consumes the existing configured branch-role policy.
- Remote publication or hosted-CI mutation.
