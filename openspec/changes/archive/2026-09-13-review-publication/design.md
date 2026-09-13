## Context

The selected Git object and the destination ref have different responsibilities.
An object may be offered for review before its Change is complete. Moving that
object into accepted or release truth requires stronger evidence. Checkout role,
task completion and a carried proof label are not substitutes for target meaning.

## Goals And Non-Goals

Close review ingress and detached-CI observation through the existing publication
owner. Preserve source trust, exact introduced ranges, protected closeout,
independent verification where selected, fresh effects and partial-peer recovery.
Do not add another work lane type, intent store, proof database or CI parser.

## Decisions

### Destination obligations are positive and shared

The repository role policy resolves a complete target ref. Review targets admit
an exact signed object with applicable introduced-range policy; active Change
artifacts may remain. Accepted/release targets require archived intent and their
existing repository-transition proof/closeout. A mixed request satisfies every
target obligation; review does not lower the accepted target's floor.

Read-only ref-update admission consumes exact proposed and prior Git objects,
target ref and remote/baseline coordinates. It reads the proposed tree, not a
detached checkout's apparent branch. The observed prior policy classifies the
target; proposed bytes do not silently rename a protected target into a review
role. New refs require the existing trusted-baseline mechanism. Missing objects
or malformed required declarations remain explicit failures.

### One deep admission owner, thin transports

Separate the existing publication admission from unrelated shell/local-ref
admission without forwarding aliases. Reuse the commit range validator and
official OpenSpec tree observer. CLI, native pre-push and remote executor call
that owner. The detached-CI command observes obligations only: no Lease lookup,
Attestation issuance, local ref mutation, remote effect or acceptance claim.

### Persist the effect, not a permission to weaken admission

A review request carries exact objects, peers and expected old OIDs without a
fabricated proof or Commitment. An accepted request retains its actual proof.
Replay derives proof selection from current target obligations and rechecks each
effect. Altering a carried selection cannot exempt a protected update. Existing
peer-local atomic CAS and UNKNOWN/partial recovery remain the effect owner.

## Alternatives

- Removing only the CLI candidate check leaves pre-push and replay contradictory.
- Adding a no-proof flag makes the caller select policy rather than the target.
- Copying role/Change parsing into adopter CI creates another authority.
- Requiring candidate/archived intent for review recreates the demonstrated cycle.

## Verification

Use real Git objects and isolated bare peers. The same signed unfinished review
snapshot must pass CLI, pre-push and detached-CI observation with no proof or host
Lease; accepted targets reject it. Preserve invalid subject/signature, local-only
ref, unavailable object, explicit baseline, mixed-target and replay-drift cases.
Assert no local source/ref/Lease mutation in observation and identical peer OIDs
after authorized review publication. Focused RED/GREEN precedes frozen full proof.

## Migration

Update internal consumers together and delete candidate-only/proof-for-review
expectations. Existing accepted/release request semantics remain protected. No
adopter change is claimed necessary or safe until the public surface is accepted,
installed and exercised. Historical receipts remain observations, not authority.
