## Why

A single `origin` remote makes a GitLab outage look like a repository release
outage and makes GitHub appear to be merely a source snapshot. ETHOS needs an
explicit peer-complete topology in which local verification and installation
continue without a remote, GitLab remains the organizational primary publication
authority, and GitHub is an independent complete repository and CI/CD plane.

## What Changes

- Declare a three-layer, peer-complete provider topology in
  `.ethos/release.toml`.
- Require separate GitLab and GitHub profiles to declare the same repository,
  CI/CD, update, and distribution capability and corresponding collaboration
  surfaces.
- Make `ethos publish` observe GitLab and GitHub peer-plane availability
  separately.
- Preserve provider-specific evidence: GitHub facts do not establish GitLab
  primary publication or GitLab hosted status, and GitLab facts do not establish
  GitHub hosted status.
- Keep local verification and installation remote-independent.
- Keep `candidate/dev` local-only; both remotes accept only `dev`, `main`, and
  `submit/*`.

## Capabilities

- `repository-governance`: subject=three-layer-dual-remote-publication;
  reuse=extend; change=modify; facet:lifecycle=publish;
  facet:surface=release-policy,cli,provider-profiles;
  facet:authority=local,gitlab,github

## Out Of Scope

- No remote configuration, push, mirroring job, tag creation, branch
  protection mutation, or hosted-CI status claim.
- No change to GitLab-primary ownership of organizational publication.
