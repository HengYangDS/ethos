## Context

See proposal.md for the blocked adopter path. The current-resolution owner
asks for validator-named repair before archive provenance, while canonical
repair requires an active Commitment. Archive provenance is additionally
excluded when strict validation reports a canonical-spec failure.

## Goals / Non-Goals

**Goals:** restore an exact repair path after official archive, preserving
current coordination, source provenance, strict validation and ordinary proof.

**Non-Goals:** infer permission from historical evidence, replay archive,
recreate active artifacts, broaden material scope or introduce persisted state.

## Decisions

### Compose source evidence before repair scope

Current resolution obtains archived intent through its existing validated
archive-effect reader when no active Commitment exists. It does so for the
narrow canonical-validation failure context as well as ordinary closeout.
The repair owner uses the verified source identity and archived changed paths;
it does not read arbitrary archive directories or trust a scope label alone.
Keep ordinary validation failures blocking outside the exact repair scope.

Replacing the missing active carrier would create parallel intent. Treating
all failed validation as permission would lose unrelated obligations. Merely
moving the archive lookup cannot fix the active-only repair predicate.

### Preserve one validator-named repair owner

Active and archived source contexts share capability-path validation and exact
requested-path coverage. An archived repair requires a failed structured spec
item and a current source relationship to that canonical path. The issue path
such as `overview` identifies a section, not a filesystem target; the official
spec item owns the canonical capability path. Current Lease, runtime and patch
admission remain independent conjunctions at public prewrite and host hooks.

Successful validation removes the exceptional repair scope. Subsequent normal
proof and closeout still validate the new exact source. Historical Attestations
are preserved; they do not certify edited content or grant reusable permission.

### Verify distinctions at the smallest relevant boundary

First reproduce active versus archived resolution and preservation of unrelated
gaps. Then use an actual archived fixture and public prewrite for a validator-
named canonical repair, mixed paths and stale coordination. Reuse the existing
archive fixtures and authority checks rather than duplicate their state machine.
The complete source and postarchive proof remain delivery preconditions.

## Risks / Trade-offs

- Archive evidence lookup can be expensive: resolve once per request and only
  when source selection and validation context require it.
- An unrelated archived Change could appear nearby: require matching identity,
  exact canonical-path provenance and the existing ambiguity checks.
- A repair is not validated merely because writing is admitted: preserve exact
  patch checks and require official strict validation and new proof afterward.
- Test budget is nearly full: reuse current fixtures and parametrize distinct
  observations without discarding coverage or increasing the 50000 ceiling.

## Migration Plan

No persisted schema changes. Deliver through the current owned lane, official
archive, exact proof, native accepted closeout and immutable runtime activation.
Consumers rebind through public runtime discovery and retry fresh exact-path
prewrite; no adopter compatibility files or historical evidence edits are needed.
