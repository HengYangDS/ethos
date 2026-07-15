## Context

ETHOS already separates local proof, remote reachability, remote publication,
and hosted-provider observations. It must model a GitLab-primary organization
that also maintains GitHub as an independent complete repository and CI/CD
plane, rather than as a source-only or distribution-only replica.

## Design

The release policy declares three roles:

1. **Local**: verification and installation; it is remote-independent.
2. **GitLab peer plane**: complete repository and CI/CD plane through `origin`;
   it alone represents organizational primary publication.
3. **GitHub peer plane**: complete repository and CI/CD plane through the
   optional `github` remote.

`candidate/dev` is an internal local integration root. The common remote-ref
policy permits `dev`, `main`, and `submit/*` on both providers and excludes
`candidate/dev` from both provider CI triggers and remote transitions.

The two provider profiles independently declare the same repository, CI/CD,
update, and distribution capabilities and their matching CI, review-template,
and issue-template surfaces. `ethos publish` remains read-only. It probes or
labels both remotes, emits the provider-specific availability projection, and
never changes `remote_push` from `not_performed`. Explicit false claim flags
prevent a GitHub observation from being reinterpreted as GitLab success, or a
GitLab observation from being reinterpreted as GitHub success.

## Proof Strategy

- Release-policy tests cover the independent GitLab and GitHub profiles,
  equal capabilities, and CI, review-template, and issue surfaces.
- Publish tests cover provider-specific availability without cross-provider
  publication or hosted-status claims.
- Architecture tests cover GitHub and GitLab collaboration surfaces.
- Focused lint, OpenSpec validation, and HEAD-bound proof run in the owned lane.
