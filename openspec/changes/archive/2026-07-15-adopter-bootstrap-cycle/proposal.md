## Why

A legacy adopter with a tracked ETHOS profile but no material-path declaration
cannot begin a governed adoption: a freshly official OpenSpec Change has status
`no-tasks`, while the profile-only bootstrap recognizes only lifecycle-selected
Changes. The resulting circularity blocks the first admitted write.

## What Changes

- Treat exactly one official, unarchived `no-tasks` Change as a bootstrap
  candidate only for the tracked `.ethos/profile.toml` first write.
- Preserve ordinary material-path coverage: `no-tasks` Changes do not cover
  any other path and do not become active lifecycle Changes.
- Add regression coverage for the official `openspec new change` sequence.

## Capabilities

### Modified Capabilities

- `repository-governance`: subject=adopter-profile-material-path-bootstrap; reuse=extend; change=modify; facet:lifecycle=openspec,adoption; facet:surface=prewrite,scope; facet:authority=profile,change.

## Out Of Scope

- Broadening material-path coverage, admitting multiple Changes, accepting
  untracked/malformed profiles, bypassing lane prewrite, or changing remote
  publication policy.

## Impact

- `packages/ethos/src/ethos/adapters/openspec/lifecycle/core.py`
- `packages/ethos/src/ethos/adapters/openspec/lifecycle/scope.py`
- OpenSpec lifecycle and material-scope regression tests.
