## Context

See proposal.md for motivation. The transferred source is the clean
`aece154744bc7b2460de1dc478f52ed4426eaa44` lane, with 18 reviewed changed paths.
The dirty transition lane also contains a necessary raw-header-byte regression.
Current source already owns payload comparison, signer verification, generic
ref-intent admission, exact Git CAS, worktree synchronization and Attestations.
The public accepted-tip composition is missing.

## Goals And Boundaries

Absorb one signature-repair capability into those existing owners. A one-tip
signature repair preserves every non-signature byte; a separately authorized
complete-DAG identity rewrite can change different fields and is not this
operation. Neither equality nor a valid signature alone grants authority.

## Decisions

### Preserve native bytes

Git commit headers use LF as the record delimiter. The current use of
`bytes.splitlines()` also consumes CR and therefore changes preserved content.
Split only on the native delimiter and remove only complete signature records.
Retain all other bytes, including continuation lines and the complete message.
Test actual isolated Git objects, not only mocked parser output.

Reject a second parser or text normalization. The existing payload owner must
provide the same answer to every ref-policy and repair consumer.

### Compose existing effects

Expose one thin `lane repair-signature` command. Its readiness is observation
only. Authorized application creates the signed object through the existing Git
signing boundary, verifies complete payload equality and current trust, records
the result as an Attestation, and compiles the existing selected-ref CAS effect.
Worktree synchronization remains a distinct existing effect with current checks.

Keep readiness separate from signing: the old derive command created Git objects
while describing itself as non-mutating. Do not retain that ambiguity. A signing
attempt whose durable result is unavailable remains unknown; recovery must find
and verify exact native/evidence results before proceeding.

### Bind policy rather than a fixed train

Resolve policy from the exact accepted prestate. Always bind its accepted ref.
An equal candidate may follow as its local projection; an unrelated candidate is
not overwritten. Include a release ref only when current policy couples it and
its exact coordinate is admitted. Bind all clean linked worktrees of selected
refs, without treating independent remotes as one distributed transaction.

### Reuse durable results

Use the existing Attestation store for the signed-object result and existing
Git/ref/worktree effect evidence for continuation. Current authorization and
freshness are re-evaluated; a stored result is not permission. Do not import
`AcceptedCarrierRepair`, `AcceptedCarrierProgress`, or the source lane's separate
request/progress directories. Recovery reports pending effects from observations
rather than trusting a command-private progress counter.

### Preserve transferred meaning, not implementation shape

Retain payload/trust separation, exact selected refs, clean worktree preconditions,
tampered-coordinate rejection, partial synchronization and lost-ack recovery,
public JSON and package-only conformance. Replace the old full-train selection,
pre-authorization object creation and task-dependent archive/closeout cycle.
Unique source remains until its obligations are accepted or explicitly resolved
and public content-reviewed retirement is admitted.

## Risks And Verification

- Raw headers, parent order or message bytes can be lost by reconstruction: use
  byte-level negative cases and reject unsupported signing inputs before CAS.
- Signing and CAS have different failure windows: test lost result persistence,
  ref acknowledgement loss and partial worktree synchronization separately.
- Replayed evidence may be stale: recheck actor, policy, trust, selected OIDs and
  worktree/index preimages immediately before their effects.
- Heavy lifecycle fixtures obscure root failures: run small native-object and
  pure-admission cases first, then one complete public/package recovery path.

## Migration

Extend current semantic owners and their consumers without a compatibility path.
After focused and public regressions, freeze and use the existing exact-proof,
official archive, accepted closeout and runtime/publication sequence. Source-lane
retirement follows accepted semantic absorption, not a checked task or this design.
