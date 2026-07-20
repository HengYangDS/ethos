## Why

DDWG's accepted root still carries the exact former adopter-profile envelope
that predates the typed normative-source field. Its `roots.rules = "."`
workaround now fails closed before the candidate's canonical replacement can be
audited and promoted, creating a bootstrap deadlock.

## What Changes

- Extend the existing *complete* former-envelope normalization to translate its
  former root-level normative-source workaround into the current typed form.
- Preserve strictness for all current declarations and every partial,
  malformed, or extended former declaration.
- Add focused regression coverage and update the profile contract and
  repository-governance specification.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `repository-governance`: normalize the one complete former profile shape
  containing `roots.rules = "."` into the current bounded declaration;
  subject=ddwg-profile-bootstrap-bridge; reuse=extend; change=modify;
  facet:lifecycle=validation,closeout; facet:surface=profile,test,docs,openspec;
  facet:authority=source,test,docs,openspec.

## Impact

The change touches only the repository-profile loader, its focused contract
tests, the canonical profile documentation, and the governing specification.
It neither changes DDWG source nor writes an adopter profile; it only admits
the historic declaration long enough for ordinary closeout to evaluate the
candidate's already-canonical profile.

## Out of Scope

- Accepting `.` in any current typed profile or accepting arbitrary legacy
  fields, roots, or normative filenames.
- Mutating DDWG, any other adopter, runner installation, remote publication,
  or historical session state.
