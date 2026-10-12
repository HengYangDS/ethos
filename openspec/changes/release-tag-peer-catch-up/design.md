## Context

See [proposal.md](proposal.md). A release tag reaches peers through the shared
push admission. Native pre-push and `ethos publish` both call it, and
`ethos publish` re-runs it before each peer effect. Three
checks there compare the tag's peeled commit with the current accepted head:
the accepted-closeout baseline, the accepted-source check behind accepted
delivery, and the release-tag subject. The publication context also binds the
proof of the checkout head, and the receipt projection requires the source to
peel to that head. Accepted history moves on after a release, so a peer that
was unavailable for the original publication can never satisfy these checks.

`ethos land --release` creates the tag through a `release.promote` Git effect.
Its Attestation records the exact tag ref update from zero to the new tag
object and asserts the accepted ref at the release commit. It also binds the
proof and accepted effect selected at that time.

## Goals / Non-Goals

**Goals:**

- Admit the exact tag object of an attested release whose commit remains in
  accepted history, for any declared peer that lacks it or already has it.
- Recheck trust, tag name, committed version, declared release-tag policy,
  repository-transition proof and accepted closeout for that release commit,
  and exact peer compare-and-swap, before each effect.
- Give native pre-push and exact publication one decision for the same input.

**Non-Goals:**

- Do not change tag creation. `land --release` and the local reference
  transaction still require the current accepted head.
- Do not admit tags without an attested release effect, a re-signed or
  replaced local object, or a divergent peer tag.
- Do not infer release identity from another peer's advertisement, create
  forge release objects, or restore a release lost to rewritten history.

## Decisions

### The release effect identifies the release commit

The release module resolves which accepted commit a ref update delivers. A
branch or a tag at the current accepted head delivers that head unchanged. A
tag that peels to a proper ancestor delivers that ancestor, but only when a
validated `release.promote` effect created exactly that tag ref and object
while asserting the accepted ref at the same commit. Validation reuses the
historical Git-effect validator, without current postconditions. Without
such evidence the current accepted head remains the subject, so the existing
mismatch gaps still apply.

Alternatives rejected:

- **Require another peer to advertise the identical object.** Peers never
  source one another. This would also fail when every peer missed the release,
  and it would make one peer's availability depend on another peer.
- **Add an explicit catch-up option or receipt.** The native hook cannot see a
  command option, and a new receipt would be a second authority.
- **Cut a new version.** The missed peer would remain permanently without the
  released identity, which is immutable once accepted.

### One subject for every publication boundary

The accepted-closeout baseline, accepted source and release-tag subject all
consume the same release-commit resolution. Proof, accepted effect, target
policy and OpenSpec intent are therefore selected for the release commit. The
publication context binds the proof of the local tag's release commit. The
receipt projection compares the effect source with that commit. The expected
head still binds the invocation to the checkout, as before. A tag's
publication subject no longer depends on which checkout runs the command; the
native hook never depended on it either.

### Fresh checks, existing effects

Catch-up uses the existing publication effect, request store and terminal
`publication:remote-effect` Attestation. The peer ref must be absent or
identical. A divergent peer tag stays refused by the existing immutability
check. Each peer effect re-runs push admission, including trust under the
current anchor, before the exact compare-and-swap.

## Risks / Trade-offs

- [The Attestation set is read during tag admission] → it is read only when the
  tag peels to a proper ancestor of the accepted head; a new release is
  unaffected.
- [A release commit's proof may no longer satisfy the current canonical policy]
  → admission blocks with the exact proof gap and never substitutes the
  current head's proof.
- [Rewritten accepted history no longer contains the release commit] → the
  catch-up refuses; a repaired history needs its own release evidence.

## Migration Plan

An adopter receives the behavior through its selected runtime. For
openai-responses-proxy, the user selected a runtime built from its current
runtime source plus this change: that adopter's profile depends on gate schema
the accepted ETHOS line does not yet carry. Before any effect, re-observe the
peer refs and run the exact publication preview. Rolling back the runtime
restores the former refusal and leaves the published tag unchanged.
