## Why

A single `origin` remote makes an organizational GitLab outage look like a
repository release outage. ETHOS needs an explicit topology in which local
verification and installation continue without a remote, GitLab remains the
organization's primary publication authority, and GitHub is an independent
mirror for update and distribution continuity.

## What Changes

- Declare a three-layer, dual-remote topology in `.ethos/release.toml`.
- Make `ethos publish` observe the GitLab primary and GitHub mirror separately.
- Permit an available GitHub mirror to carry only update and distribution when
  the GitLab primary is unavailable.
- Preserve the non-claims: a GitHub mirror does not establish GitLab primary
  publication, GitLab hosted status, or repository proof.
- Keep local verification and installation remote-independent.

## Capabilities

- `repository-governance`: subject=three-layer-dual-remote-publication; reuse=extend; change=modify; facet:lifecycle=publish; facet:surface=release-policy,cli; facet:authority=local,gitlab,github

## Out Of Scope

- No remote push, mirroring job, tag creation, or hosted-CI status claim.
- No change to the GitLab-primary ownership of organizational publication.
