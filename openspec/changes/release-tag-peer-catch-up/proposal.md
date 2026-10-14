## Why

A declared peer that is unavailable when a release is published can never
receive that release tag later. Publication admits a tag only while it peels to
the current accepted head, and accepted history keeps moving. The
openai-responses-proxy release v5.0.2 therefore reached GitHub only; every later
GitLab pipeline fails its provenance check because the released changelog
section has no product tag. A hook bypass or a server-created tag would break
the parity of tag objects across peers.

## What Changes

- Keep the current rule for new releases: a tag publishes from the current
  accepted head.
- Admit a tag at an older accepted commit only for the exact tag object that an
  attested ETHOS release effect created at that commit, while the commit remains
  in accepted history.
- Recheck tag trust, name, committed version, release-tag policy, proof and
  accepted closeout for that commit before the effect. The peer ref must be
  absent or already the identical object; publication is attested as before.
- Native pre-push and `ethos publish` share this admission, so a direct push and
  the command reach the same decision.

Out of scope: tags without an attested ETHOS release effect, replacing a
divergent peer tag, forge release objects such as notes and assets, and how new
releases are created.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: release-tag publication and accepted delivery admit
  the attested release object for a peer that missed the original release.

## Impact

The release-subject owner, shared push admission, publication context and
receipt projection, and their public regressions. Routing remains the
repository-governance owner. No new command option, carrier, persisted record,
lifecycle state or authority is introduced. An adopter receives the behavior
through its selected runtime; that installation is a separate decision.
