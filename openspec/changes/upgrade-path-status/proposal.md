# Proposal

## Why

A governed repository whose last landed bump is outside the support window is no subject, so a
release need not be qualified to upgrade from the release it pins. Nothing tells that repository
so. The archived `rc-plan` design, appendix B.3, asks that `status` name, for such a repository,
the newest release whose recorded `[release.upgrade_from]` lists its release, or state that no
qualified path exists. The archived `rc-scope-plan` design lists a stated path from a release
outside the support window as missing for the adopter that another person maintains.

The release lead ruled on 2026-11-15 that this part leaves `release-predecessors`, which had
reached its size.

## What Changes

- `status` names, for a governed repository on a release outside the support window, the newest
  release with a qualified path from that release, or states that none exists.
- The open design question is the source of that answer. An installed build holds at most its own
  release's record, and the package does not ship the release binding, so a build cannot name a
  release newer than itself. The design chooses where the records of newer releases are read.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None while this Change is a draft, so `skip_specs: true` applies. Its delta arrives with its tasks.

## Impact

The inspection operation, the reader of the runtime pin and the distribution specification. It is
not sized: the size follows from the source that the design chooses. It adds a reading and no
refusal.

Owner: the release lead. Next action: design the source of the newer releases' records. Read
again: at the cut of 0.2.0-beta.14.
